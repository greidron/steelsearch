use os_core::OPENSEARCH_3_7_0_TRANSPORT;
use os_transport::action::{
    build_opensearch_create_reader_context_request_message,
    build_opensearch_create_reader_context_response_message,
    build_opensearch_delete_pit_response_message,
    build_opensearch_free_pit_context_request_message,
    build_opensearch_update_reader_context_request_message,
    build_opensearch_update_reader_context_response_message,
    read_opensearch_create_reader_context_request_message,
    read_opensearch_create_reader_context_response_message,
    read_opensearch_delete_pit_response_message, read_opensearch_free_pit_context_request_message,
    read_opensearch_update_reader_context_request_message,
    read_opensearch_update_reader_context_response_message,
    OpenSearchCreateReaderContextRequestWire, OpenSearchCreateReaderContextResponseWire,
    OpenSearchDeletePitInfoWire, OpenSearchDeletePitResponseWire,
    OpenSearchFreePitContextRequestWire, OpenSearchPitSearchContextIdForNodeWire,
    OpenSearchSearchContextIdForNodeWire, OpenSearchShardIdWire,
    OpenSearchShardSearchContextIdWire, OpenSearchUpdateReaderContextRequestWire,
    OpenSearchUpdateReaderContextResponseWire, TimeValueWire,
};
use os_transport::frame::{decode_frame, DecodedFrame};
use std::hint::black_box;
use std::time::Instant;

const ITERATIONS: usize = 400_000;

fn main() {
    let shard_context = OpenSearchShardSearchContextIdWire::new("reader-session", 42);
    let create_request = OpenSearchCreateReaderContextRequestWire::new(
        OpenSearchShardIdWire {
            index_name: "logs-reader".to_string(),
            index_uuid: "uuid-reader".to_string(),
            shard_id: 0,
        },
        TimeValueWire::seconds(30),
    );
    let create_response = OpenSearchCreateReaderContextResponseWire::new(shard_context.clone());
    let update_request = OpenSearchUpdateReaderContextRequestWire {
        parent_task_node: String::new(),
        parent_task_id: None,
        pit_id: "pit-context".to_string(),
        keep_alive_millis: 120_000,
        creation_time_millis: 1_700_000_000_000,
        search_context_id: shard_context.clone(),
    };
    let update_response = OpenSearchUpdateReaderContextResponseWire {
        pit_id: "pit-context".to_string(),
        creation_time_millis: 1_700_000_000_000,
        keep_alive_millis: 120_000,
    };
    let free_request = OpenSearchFreePitContextRequestWire {
        parent_task_node: String::new(),
        parent_task_id: None,
        context_ids: vec![OpenSearchPitSearchContextIdForNodeWire {
            pit_id: "pit-context".to_string(),
            search_context: OpenSearchSearchContextIdForNodeWire {
                node: "steel-node-id".to_string(),
                cluster_alias: None,
                search_context_id: shard_context,
            },
        }],
    };
    let free_response =
        OpenSearchDeletePitResponseWire::with_results(vec![OpenSearchDeletePitInfoWire::new(
            true,
            "pit-context",
        )]);

    let create_request_encode = measure("pit_reader_create_request_encode", ITERATIONS, || {
        let frame = build_opensearch_create_reader_context_request_message(
            60,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&create_request),
        )
        .expect("create-reader-context request encode should succeed");
        black_box(frame);
    });
    let create_request_frame = build_opensearch_create_reader_context_request_message(
        60,
        OPENSEARCH_3_7_0_TRANSPORT,
        &create_request,
    )
    .expect("create-reader-context request encode should succeed");
    let create_request_decode = measure("pit_reader_create_request_decode", ITERATIONS, || {
        let mut frame = black_box(create_request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_opensearch_create_reader_context_request_message(black_box(&message))
            .expect("create-reader-context request decode");
        black_box(decoded);
    });

    let create_response_encode = measure("pit_reader_create_response_encode", ITERATIONS, || {
        let frame = build_opensearch_create_reader_context_response_message(
            60,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&create_response),
        )
        .expect("create-reader-context response encode should succeed");
        black_box(frame);
    });
    let create_response_frame = build_opensearch_create_reader_context_response_message(
        60,
        OPENSEARCH_3_7_0_TRANSPORT,
        &create_response,
    )
    .expect("create-reader-context response encode should succeed");
    let create_response_decode = measure("pit_reader_create_response_decode", ITERATIONS, || {
        let mut frame = black_box(create_response_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_opensearch_create_reader_context_response_message(black_box(&message))
            .expect("create-reader-context response decode");
        black_box(decoded);
    });

    let update_request_encode = measure("pit_reader_update_request_encode", ITERATIONS, || {
        let frame = build_opensearch_update_reader_context_request_message(
            61,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&update_request),
        )
        .expect("update-reader-context request encode should succeed");
        black_box(frame);
    });
    let update_request_frame = build_opensearch_update_reader_context_request_message(
        61,
        OPENSEARCH_3_7_0_TRANSPORT,
        &update_request,
    )
    .expect("update-reader-context request encode should succeed");
    let update_request_decode = measure("pit_reader_update_request_decode", ITERATIONS, || {
        let mut frame = black_box(update_request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_opensearch_update_reader_context_request_message(black_box(&message))
            .expect("update-reader-context request decode");
        black_box(decoded);
    });

    let update_response_encode = measure("pit_reader_update_response_encode", ITERATIONS, || {
        let frame = build_opensearch_update_reader_context_response_message(
            61,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&update_response),
        )
        .expect("update-reader-context response encode should succeed");
        black_box(frame);
    });
    let update_response_frame = build_opensearch_update_reader_context_response_message(
        61,
        OPENSEARCH_3_7_0_TRANSPORT,
        &update_response,
    )
    .expect("update-reader-context response encode should succeed");
    let update_response_decode = measure("pit_reader_update_response_decode", ITERATIONS, || {
        let mut frame = black_box(update_response_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_opensearch_update_reader_context_response_message(black_box(&message))
            .expect("update-reader-context response decode");
        black_box(decoded);
    });

    let free_request_encode = measure("pit_reader_free_request_encode", ITERATIONS, || {
        let frame = build_opensearch_free_pit_context_request_message(
            62,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&free_request),
        )
        .expect("free-PIT-context request encode should succeed");
        black_box(frame);
    });
    let free_request_frame = build_opensearch_free_pit_context_request_message(
        62,
        OPENSEARCH_3_7_0_TRANSPORT,
        &free_request,
    )
    .expect("free-PIT-context request encode should succeed");
    let free_request_decode = measure("pit_reader_free_request_decode", ITERATIONS, || {
        let mut frame = black_box(free_request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_opensearch_free_pit_context_request_message(black_box(&message))
            .expect("free-PIT-context request decode");
        black_box(decoded);
    });

    let free_response_encode = measure("pit_reader_free_response_encode", ITERATIONS, || {
        let frame = build_opensearch_delete_pit_response_message(
            62,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&free_response),
        )
        .expect("free-PIT-context response encode should succeed");
        black_box(frame);
    });
    let free_response_frame = build_opensearch_delete_pit_response_message(
        62,
        OPENSEARCH_3_7_0_TRANSPORT,
        &free_response,
    )
    .expect("free-PIT-context response encode should succeed");
    let free_response_decode = measure("pit_reader_free_response_decode", ITERATIONS, || {
        let mut frame = black_box(free_response_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_opensearch_delete_pit_response_message(black_box(&message))
            .expect("free-PIT-context response decode");
        black_box(decoded);
    });

    let combined_ops_per_second = create_request_encode
        .ops_per_second
        .min(create_request_decode.ops_per_second)
        .min(create_response_encode.ops_per_second)
        .min(create_response_decode.ops_per_second)
        .min(update_request_encode.ops_per_second)
        .min(update_request_decode.ops_per_second)
        .min(update_response_encode.ops_per_second)
        .min(update_response_decode.ops_per_second)
        .min(free_request_encode.ops_per_second)
        .min(free_request_decode.ops_per_second)
        .min(free_response_encode.ops_per_second)
        .min(free_response_decode.ops_per_second);
    println!("pit_reader_context_wire_bottleneck_ops_per_second={combined_ops_per_second:.2}");
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
