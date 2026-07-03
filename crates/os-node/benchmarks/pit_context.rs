use os_engine::{
    CreateIndexRequest, DocumentMetadata, IndexEngine, RefreshRequest, ReplayDocumentRequest,
    SearchRequest, WriteCoordinationMetadata,
};
use os_engine_tantivy::TantivyEngine;
use os_node::standalone_runtime::{DocumentMap, PitContext, StoredDocument};
use serde_json::json;
use std::collections::BTreeMap;
use std::hint::black_box;
use std::sync::Arc;
use std::time::Instant;

const DOCUMENTS: usize = 10_000;
const ITERATIONS: usize = 500_000;
const SNAPSHOT_ITERATIONS: usize = 250;
const NATIVE_REPLAY_SEARCH_ITERATIONS: usize = 20;
const NATIVE_REUSED_SEARCH_ITERATIONS: usize = 2_000;

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
    bench_native_replay_slice_search(&documents);
    bench_native_reused_slice_search(&documents);

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

fn bench_native_replay_slice_search(documents: &DocumentMap) {
    let start = Instant::now();
    let mut total_hits = 0;
    for iteration in 0..NATIVE_REPLAY_SEARCH_ITERATIONS {
        total_hits += build_native_snapshot_and_slice_search(documents, iteration % 2);
    }
    let elapsed = start.elapsed();
    let elapsed_ms = elapsed.as_secs_f64() * 1_000.0;
    let ops_per_second = NATIVE_REPLAY_SEARCH_ITERATIONS as f64 / elapsed.as_secs_f64();
    let documents_per_second =
        (NATIVE_REPLAY_SEARCH_ITERATIONS * documents.len()) as f64 / elapsed.as_secs_f64();
    println!("pit_native_replay_slice_search_iterations={NATIVE_REPLAY_SEARCH_ITERATIONS}");
    println!("pit_native_replay_slice_search_elapsed_ms={elapsed_ms:.3}");
    println!("pit_native_replay_slice_search_ops_per_second={ops_per_second:.2}");
    println!("pit_native_replay_slice_search_documents_per_second={documents_per_second:.2}");
    println!("pit_native_replay_slice_search_total_hits={total_hits}");
}

fn bench_native_reused_slice_search(documents: &DocumentMap) {
    let engine = build_native_snapshot_engine(documents);
    let start = Instant::now();
    let mut total_hits = 0;
    for iteration in 0..NATIVE_REUSED_SEARCH_ITERATIONS {
        total_hits += run_native_slice_search(&engine, iteration % 2);
    }
    let elapsed = start.elapsed();
    let elapsed_ms = elapsed.as_secs_f64() * 1_000.0;
    let ops_per_second = NATIVE_REUSED_SEARCH_ITERATIONS as f64 / elapsed.as_secs_f64();
    println!("pit_native_reused_slice_search_iterations={NATIVE_REUSED_SEARCH_ITERATIONS}");
    println!("pit_native_reused_slice_search_elapsed_ms={elapsed_ms:.3}");
    println!("pit_native_reused_slice_search_ops_per_second={ops_per_second:.2}");
    println!("pit_native_reused_slice_search_total_hits={total_hits}");
}

fn build_native_snapshot_and_slice_search(documents: &DocumentMap, slice_id: usize) -> usize {
    let engine = build_native_snapshot_engine(documents);
    run_native_slice_search(&engine, slice_id)
}

fn build_native_snapshot_engine(documents: &DocumentMap) -> TantivyEngine {
    let engine = TantivyEngine::default();
    engine
        .create_index(CreateIndexRequest {
            index: "pit-bench".to_string(),
            settings: json!({}),
            mappings: json!({
                "properties": {
                    "tenant": { "type": "keyword" },
                    "rank": { "type": "long" }
                }
            }),
        })
        .expect("create PIT benchmark native snapshot index");
    for (key, document) in documents {
        let id = document_id_from_key(key);
        engine
            .replay_document(ReplayDocumentRequest {
                index: "pit-bench".to_string(),
                metadata: DocumentMetadata {
                    id,
                    version: document.version as u64,
                    seq_no: document.seq_no,
                    primary_term: document.primary_term as u64,
                },
                coordination: WriteCoordinationMetadata::default(),
                source: document.source.clone(),
            })
            .expect("replay PIT benchmark document into native snapshot");
    }
    engine
        .refresh(RefreshRequest {
            indices: vec!["pit-bench".to_string()],
        })
        .expect("refresh PIT benchmark native snapshot");
    engine
}

fn run_native_slice_search(engine: &TantivyEngine, slice_id: usize) -> usize {
    let response = engine
        .search(SearchRequest {
            indices: vec!["pit-bench".to_string()],
            query: json!({
                "query": { "match_all": {} },
                "slice": {
                    "field": "_id",
                    "id": slice_id,
                    "max": 2
                }
            }),
            stored_fields: None,
            source_fields: None,
            source_filter: None,
            source_includes: None,
            source_include: None,
            source_excludes: None,
            source_exclude: None,
            aggregations: json!({}),
            highlight: None,
            sort: Vec::new(),
            from: 0,
            size: 10,
            explain: false,
        })
        .expect("search PIT benchmark native snapshot slice");
    let hits = response.hits.len();
    black_box(response);
    hits
}

fn document_id_from_key(key: &str) -> String {
    key.split(':').nth(1).unwrap_or(key).to_string()
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
