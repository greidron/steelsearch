use os_node::standalone_runtime::{PitContext, StoredDocument};
use serde_json::json;
use std::collections::BTreeMap;
use std::hint::black_box;
use std::sync::Arc;
use std::time::Instant;

const DOCUMENTS: usize = 10_000;
const ITERATIONS: usize = 500_000;

fn main() {
    let mut documents = BTreeMap::new();
    for id in 0..DOCUMENTS {
        documents.insert(
            format!("pit-bench:{id}:_doc"),
            StoredDocument {
                source: json!({ "tenant": "a", "rank": id }),
                version: 1,
                seq_no: id as i64,
                primary_term: 1,
                routing: None,
                refreshed: true,
            },
        );
    }
    let context = PitContext {
        indices: vec!["pit-bench".to_string()],
        documents: Arc::new(documents),
        keep_alive_millis: 60_000,
        expires_at_millis: 1_700_000_060_000,
        creation_time_millis: 1_700_000_000_000,
    };

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
