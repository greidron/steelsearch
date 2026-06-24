use os_core::OPENSEARCH_3_7_0_TRANSPORT;
use os_transport::action::{
    build_list_tasks_request_message, build_list_tasks_response_message,
    read_list_tasks_request_message, read_list_tasks_response_message, ListTaskInfoWire,
    ListTasksRequestWire, ListTasksResponseWire, TaskIdWire,
};
use os_transport::frame::{decode_frame, DecodedFrame};
use std::collections::BTreeMap;
use std::hint::black_box;
use std::time::Instant;

const ITERATIONS: usize = 400_000;

fn main() {
    let request = ListTasksRequestWire::default();
    let filtered_request = ListTasksRequestWire {
        task_id: TaskIdWire {
            node_id: "node-a".to_string(),
            id: Some(7),
        },
        nodes: vec!["node-a".to_string()],
        actions: vec!["cluster:admin/*".to_string()],
        ..ListTasksRequestWire::default()
    };
    let response = ListTasksResponseWire {
        task_failure_count: 0,
        node_failures: Vec::new(),
        tasks: vec![ListTaskInfoWire {
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
        }],
    };

    let request_encode = measure("list_tasks_request_encode", ITERATIONS, || {
        let frame =
            build_list_tasks_request_message(12, OPENSEARCH_3_7_0_TRANSPORT, black_box(&request))
                .expect("list tasks request encode should succeed");
        black_box(frame);
    });
    let filtered_request_encode = measure("list_tasks_filtered_request_encode", ITERATIONS, || {
        let frame = build_list_tasks_request_message(
            12,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&filtered_request),
        )
        .expect("filtered list tasks request encode should succeed");
        black_box(frame);
    });
    let response_encode = measure("list_tasks_response_encode", ITERATIONS, || {
        let frame =
            build_list_tasks_response_message(12, OPENSEARCH_3_7_0_TRANSPORT, black_box(&response))
                .expect("list tasks response encode should succeed");
        black_box(frame);
    });

    let request_frame = build_list_tasks_request_message(12, OPENSEARCH_3_7_0_TRANSPORT, &request)
        .expect("list tasks request encode should succeed");
    let filtered_request_frame =
        build_list_tasks_request_message(12, OPENSEARCH_3_7_0_TRANSPORT, &filtered_request)
            .expect("filtered list tasks request encode should succeed");
    let response_frame =
        build_list_tasks_response_message(12, OPENSEARCH_3_7_0_TRANSPORT, &response)
            .expect("list tasks response encode should succeed");

    let request_decode = measure("list_tasks_request_decode", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_list_tasks_request_message(black_box(&message))
            .expect("list tasks request decode");
        black_box(decoded);
    });
    let filtered_request_decode = measure("list_tasks_filtered_request_decode", ITERATIONS, || {
        let mut frame = black_box(filtered_request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_list_tasks_request_message(black_box(&message))
            .expect("filtered list tasks request decode");
        black_box(decoded);
    });
    let response_decode = measure("list_tasks_response_decode", ITERATIONS, || {
        let mut frame = black_box(response_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_list_tasks_response_message(black_box(&message))
            .expect("list tasks response decode");
        black_box(decoded);
    });

    let combined_ops_per_second = request_encode
        .ops_per_second
        .min(filtered_request_encode.ops_per_second)
        .min(response_encode.ops_per_second)
        .min(request_decode.ops_per_second)
        .min(filtered_request_decode.ops_per_second)
        .min(response_decode.ops_per_second);
    println!("list_tasks_wire_bottleneck_ops_per_second={combined_ops_per_second:.2}");
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
