use os_core::OPENSEARCH_3_7_0_TRANSPORT;
use os_engine::DocumentMetadata;
use os_transport::action::{
    build_opensearch_bulk_request_message, build_opensearch_bulk_response_message,
    read_opensearch_bulk_request_message, read_opensearch_bulk_response_message,
    OpenSearchBulkItemResponseWire, OpenSearchBulkRequestItemWire, OpenSearchBulkRequestWire,
    OpenSearchBulkResponseWire, OpenSearchDeleteRequestWire, OpenSearchDeleteResponseWire,
    OpenSearchIndexRequestWire, OpenSearchIndexResponseWire,
};
use os_transport::frame::{decode_frame, DecodedFrame};
use serde_json::json;
use std::hint::black_box;
use std::time::Instant;

const ITERATIONS: usize = 100_000;
const ITEM_COUNT: usize = 8;

fn main() {
    let request = OpenSearchBulkRequestWire::new(
        (0..ITEM_COUNT)
            .map(|id| {
                if id % 2 == 0 {
                    OpenSearchBulkRequestItemWire::Index(OpenSearchIndexRequestWire::new(
                        "bench-000001".to_string(),
                        format!("doc-{id}"),
                        json!({
                            "message": "alpha beta gamma",
                            "tenant": "tenant-a",
                            "value": id
                        }),
                    ))
                } else {
                    OpenSearchBulkRequestItemWire::Delete(OpenSearchDeleteRequestWire::new(
                        "bench-000001".to_string(),
                        format!("doc-{id}"),
                    ))
                }
            })
            .collect(),
    );
    let response = OpenSearchBulkResponseWire::success(
        (0..ITEM_COUNT)
            .map(|id| {
                if id % 2 == 0 {
                    OpenSearchBulkItemResponseWire::index(
                        id as i32,
                        OpenSearchIndexResponseWire::created(
                            "bench-000001".to_string(),
                            DocumentMetadata {
                                id: format!("doc-{id}"),
                                version: 3,
                                seq_no: id as i64,
                                primary_term: 2,
                            },
                        ),
                    )
                } else {
                    OpenSearchBulkItemResponseWire::delete(
                        id as i32,
                        OpenSearchDeleteResponseWire::deleted(
                            "bench-000001".to_string(),
                            DocumentMetadata {
                                id: format!("doc-{id}"),
                                version: 4,
                                seq_no: id as i64,
                                primary_term: 2,
                            },
                        ),
                    )
                }
            })
            .collect(),
    );

    let request_encode = measure("bulk_request_encode", ITERATIONS, || {
        let frame = build_opensearch_bulk_request_message(
            7,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&request),
        )
        .expect("bulk request encode should succeed");
        black_box(frame);
    });
    let response_encode = measure("bulk_response_encode", ITERATIONS, || {
        let frame = build_opensearch_bulk_response_message(
            7,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&response),
        )
        .expect("bulk response encode should succeed");
        black_box(frame);
    });

    let request_frame =
        build_opensearch_bulk_request_message(7, OPENSEARCH_3_7_0_TRANSPORT, &request)
            .expect("bulk request encode should succeed");
    let response_frame =
        build_opensearch_bulk_response_message(7, OPENSEARCH_3_7_0_TRANSPORT, &response)
            .expect("bulk response encode should succeed");

    let request_decode = measure("bulk_request_decode", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded =
            read_opensearch_bulk_request_message(black_box(&message)).expect("bulk request decode");
        black_box(decoded);
    });
    let response_decode = measure("bulk_response_decode", ITERATIONS, || {
        let mut frame = black_box(response_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_opensearch_bulk_response_message(black_box(&message))
            .expect("bulk response decode");
        black_box(decoded);
    });

    let combined_ops_per_second = request_encode
        .ops_per_second
        .min(response_encode.ops_per_second)
        .min(request_decode.ops_per_second)
        .min(response_decode.ops_per_second);
    println!("bulk_wire_bottleneck_ops_per_second={combined_ops_per_second:.2}");
    println!(
        "bulk_wire_bottleneck_items_per_second={:.2}",
        combined_ops_per_second * ITEM_COUNT as f64
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
