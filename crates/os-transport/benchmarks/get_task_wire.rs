use os_core::OPENSEARCH_3_7_0_TRANSPORT;
use os_transport::action::{
    build_get_task_request_message, build_get_task_response_message, read_get_task_request_message,
    read_get_task_response_message, GetTaskRequestWire, GetTaskResponseWire, ListTaskInfoWire,
    TimeValueWire,
};
use os_transport::frame::{decode_frame, DecodedFrame};
use std::collections::BTreeMap;
use std::hint::black_box;
use std::time::Instant;

const ITERATIONS: usize = 400_000;

fn main() {
    let request = GetTaskRequestWire {
        timeout: Some(TimeValueWire::seconds(30)),
        ..GetTaskRequestWire::new("node-a".to_string(), 7)
    };
    let response = GetTaskResponseWire::running(ListTaskInfoWire {
        node_id: "node-a".to_string(),
        task_id: 7,
        task_type: "transport".to_string(),
        action: "cluster:admin/reroute".to_string(),
        description: Some("reroute shards [queued]".to_string()),
        start_time_millis: 1,
        running_time_nanos: 1,
        cancellable: true,
        cancelled: false,
        parent_task_node: String::new(),
        parent_task_id: None,
        headers: BTreeMap::new(),
        cancellation_start_time_millis: None,
    });
    let completed_response = GetTaskResponseWire::completed(ListTaskInfoWire {
        node_id: "node-a".to_string(),
        task_id: 8,
        task_type: "transport".to_string(),
        action: "cluster:admin/voting_config/clear_exclusions".to_string(),
        description: Some("remove-node [node-b] [acknowledged]".to_string()),
        start_time_millis: 1,
        running_time_nanos: 1,
        cancellable: false,
        cancelled: false,
        parent_task_node: "parent-node".to_string(),
        parent_task_id: Some(99),
        headers: BTreeMap::new(),
        cancellation_start_time_millis: None,
    });

    let request_encode = measure("get_task_request_encode", ITERATIONS, || {
        let frame =
            build_get_task_request_message(14, OPENSEARCH_3_7_0_TRANSPORT, black_box(&request))
                .expect("get task request encode should succeed");
        black_box(frame);
    });

    let request_frame = build_get_task_request_message(14, OPENSEARCH_3_7_0_TRANSPORT, &request)
        .expect("get task request encode should succeed");

    let request_decode = measure("get_task_request_decode", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded =
            read_get_task_request_message(black_box(&message)).expect("get task request decode");
        black_box(decoded);
    });
    let request_validate = measure("get_task_request_validate", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded =
            read_get_task_request_message(black_box(&message)).expect("get task request decode");
        decoded
            .validate_supported_execution()
            .expect("get task request should be supported");
        black_box(decoded);
    });

    let response_encode = measure("get_task_response_encode", ITERATIONS, || {
        let frame =
            build_get_task_response_message(14, OPENSEARCH_3_7_0_TRANSPORT, black_box(&response))
                .expect("get task response encode should succeed");
        black_box(frame);
    });
    let completed_response_encode = measure("get_task_completed_response_encode", ITERATIONS, || {
        let frame = build_get_task_response_message(
            14,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&completed_response),
        )
        .expect("get task completed response encode should succeed");
        black_box(frame);
    });

    let response_frame = build_get_task_response_message(14, OPENSEARCH_3_7_0_TRANSPORT, &response)
        .expect("get task response encode should succeed");
    let completed_response_frame = build_get_task_response_message(
        14,
        OPENSEARCH_3_7_0_TRANSPORT,
        &completed_response,
    )
    .expect("get task completed response encode should succeed");

    let response_decode = measure("get_task_response_decode", ITERATIONS, || {
        let mut frame = black_box(response_frame.clone());
        let message = decode_message(&mut frame);
        let decoded =
            read_get_task_response_message(black_box(&message)).expect("get task response decode");
        black_box(decoded);
    });
    let completed_response_decode = measure("get_task_completed_response_decode", ITERATIONS, || {
        let mut frame = black_box(completed_response_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_get_task_response_message(black_box(&message))
            .expect("get task completed response decode");
        black_box(decoded);
    });

    let combined_ops_per_second = request_encode
        .ops_per_second
        .min(request_decode.ops_per_second)
        .min(request_validate.ops_per_second)
        .min(response_encode.ops_per_second)
        .min(completed_response_encode.ops_per_second)
        .min(response_decode.ops_per_second)
        .min(completed_response_decode.ops_per_second);
    println!("get_task_wire_bottleneck_ops_per_second={combined_ops_per_second:.2}");
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
