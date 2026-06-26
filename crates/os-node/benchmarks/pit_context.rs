use os_node::standalone_runtime::{DocumentMap, PitContext, StoredDocument};
use serde_json::json;
use std::collections::BTreeMap;
use std::hint::black_box;
use std::sync::Arc;
use std::time::Instant;

const DOCUMENTS: usize = 10_000;
const ITERATIONS: usize = 500_000;
const SNAPSHOT_ITERATIONS: usize = 250;

fn main() {
    let documents = build_documents(DOCUMENTS);
    let estimated_payload_bytes = estimate_snapshot_payload_bytes(&documents);
    let context = PitContext {
        indices: vec!["pit-bench".to_string()],
        documents: Arc::new(documents.clone()),
        keep_alive_millis: 60_000,
        expires_at_millis: 1_700_000_060_000,
        creation_time_millis: 1_700_000_000_000,
    };

    bench_context_clone(&context);
    bench_open_snapshot_build(&documents);

    println!("pit_snapshot_documents={DOCUMENTS}");
    println!("pit_snapshot_estimated_payload_bytes={estimated_payload_bytes}");
}

fn build_documents(count: usize) -> DocumentMap {
    let mut documents = BTreeMap::new();
    for id in 0..count {
        documents.insert(
            format!("pit-bench:{id}:_doc"),
            Arc::new(StoredDocument {
                source: json!({ "tenant": "a", "rank": id }),
                version: 1,
                seq_no: id as i64,
                primary_term: 1,
                routing: None,
                refreshed: true,
            }),
        );
    }
    documents
}

fn bench_context_clone(context: &PitContext) {
    let start = Instant::now();
    for _ in 0..ITERATIONS {
        let cloned = context.clone();
        black_box(cloned);
    }
    let elapsed = start.elapsed();
    let elapsed_ms = elapsed.as_secs_f64() * 1_000.0;
    let ops_per_second = ITERATIONS as f64 / elapsed.as_secs_f64();
    println!("pit_context_clone_documents={DOCUMENTS}");
    println!("pit_context_clone_iterations={ITERATIONS}");
    println!("pit_context_clone_elapsed_ms={elapsed_ms:.3}");
    println!("pit_context_clone_ops_per_second={ops_per_second:.2}");
    println!(
        "pit_context_clone_snapshot_strong_count={}",
        Arc::strong_count(&context.documents)
    );
}

fn bench_open_snapshot_build(documents: &DocumentMap) {
    let start = Instant::now();
    for _ in 0..SNAPSHOT_ITERATIONS {
        let snapshot = documents
            .iter()
            .filter_map(|(key, record)| {
                key.starts_with("pit-bench:")
                    .then(|| (key.clone(), record.clone()))
            })
            .collect::<BTreeMap<_, _>>();
        black_box(snapshot);
    }
    let elapsed = start.elapsed();
    let elapsed_ms = elapsed.as_secs_f64() * 1_000.0;
    let snapshots_per_second = SNAPSHOT_ITERATIONS as f64 / elapsed.as_secs_f64();
    let documents_per_second =
        (SNAPSHOT_ITERATIONS * documents.len()) as f64 / elapsed.as_secs_f64();
    println!("pit_open_snapshot_iterations={SNAPSHOT_ITERATIONS}");
    println!("pit_open_snapshot_elapsed_ms={elapsed_ms:.3}");
    println!("pit_open_snapshot_ops_per_second={snapshots_per_second:.2}");
    println!("pit_open_snapshot_documents_per_second={documents_per_second:.2}");
}

fn estimate_snapshot_payload_bytes(documents: &DocumentMap) -> usize {
    documents
        .iter()
        .map(|(key, record)| {
            key.len()
                + serde_json::to_vec(record.as_ref())
                    .map(|body| body.len())
                    .unwrap_or(0)
        })
        .sum()
}
