use os_engine::{
    BulkWriteOperation, BulkWriteRequest, CreateIndexRequest, IndexDocumentRequest, IndexEngine,
    RefreshRequest, SearchRequest,
};
use os_engine_tantivy::TantivyEngine;
use serde_json::json;
use std::hint::black_box;
use std::time::{Duration, Instant};

const DOC_COUNT: usize = 128;
const INDEX: &str = "bench";

fn main() {
    record("index", DOC_COUNT, benchmark_index());
    record("bulk", DOC_COUNT, benchmark_bulk());
    record("refresh", DOC_COUNT, benchmark_refresh());

    let engine = seeded_engine();
    record("lexical_search", 32, benchmark_lexical_search(&engine));
    record("aggregation", 32, benchmark_aggregation(&engine));
    record(
        "exact_vector_search",
        32,
        benchmark_exact_vector_search(&engine),
    );
    record(
        "hnsw_vector_search",
        32,
        benchmark_hnsw_vector_search(&engine),
    );
    record("hybrid_search", 32, benchmark_hybrid_search(&engine));
}

fn benchmark_index() -> Duration {
    let engine = empty_engine();
    let started = Instant::now();
    for id in 0..DOC_COUNT {
        index_document(&engine, id);
    }
    let elapsed = started.elapsed();
    black_box(engine);
    elapsed
}

fn benchmark_bulk() -> Duration {
    let engine = empty_engine();
    let operations = (0..DOC_COUNT)
        .map(|id| BulkWriteOperation::Index(document_request(id)))
        .collect();
    let started = Instant::now();
    let response = engine.bulk_write(BulkWriteRequest { operations }).unwrap();
    let elapsed = started.elapsed();
    assert!(!response.errors);
    assert_eq!(response.items.len(), DOC_COUNT);
    black_box(response);
    elapsed
}

fn benchmark_refresh() -> Duration {
    let engine = empty_engine();
    for id in 0..DOC_COUNT {
        index_document(&engine, id);
    }
    let started = Instant::now();
    engine
        .refresh(RefreshRequest {
            indices: vec![INDEX.to_string()],
        })
        .unwrap();
    let elapsed = started.elapsed();
    black_box(engine);
    elapsed
}

fn benchmark_lexical_search(engine: &TantivyEngine) -> Duration {
    repeat_search(
        engine,
        SearchRequest {
            indices: vec![INDEX.to_string()],
            query: json!({ "match": { "message": "alpha" } }),
            aggregations: json!({}),
            sort: Vec::new(),
            from: 0,
            size: 10,
        },
    )
}

fn benchmark_aggregation(engine: &TantivyEngine) -> Duration {
    repeat_search(
        engine,
        SearchRequest {
            indices: vec![INDEX.to_string()],
            query: json!({ "match_all": {} }),
            aggregations: json!({
                "by_service": {
                    "terms": {
                        "field": "service",
                        "size": 4
                    }
                }
            }),
            sort: Vec::new(),
            from: 0,
            size: 10,
        },
    )
}

fn benchmark_exact_vector_search(engine: &TantivyEngine) -> Duration {
    let started = Instant::now();
    for _ in 0..32 {
        let hits = engine
            .exact_vector_search(INDEX, "embedding", &[0.25, 0.5, 0.75], 8)
            .unwrap();
        assert_eq!(hits.len(), 8);
        black_box(hits);
    }
    started.elapsed()
}

fn benchmark_hnsw_vector_search(engine: &TantivyEngine) -> Duration {
    let started = Instant::now();
    for _ in 0..32 {
        let hits = engine
            .hnsw_vector_search(INDEX, "embedding", &[0.25, 0.5, 0.75], 8, 16)
            .unwrap();
        assert_eq!(hits.len(), 8);
        black_box(hits);
    }
    started.elapsed()
}

fn benchmark_hybrid_search(engine: &TantivyEngine) -> Duration {
    repeat_search(
        engine,
        SearchRequest {
            indices: vec![INDEX.to_string()],
            query: json!({
                "bool": {
                    "must": [
                        { "match": { "message": "alpha" } },
                        {
                            "knn": {
                                "embedding": {
                                    "vector": [0.25, 0.5, 0.75],
                                    "k": 8,
                                    "method_parameters": { "ef_search": 16 }
                                }
                            }
                        }
                    ],
                    "filter": [
                        { "term": { "tenant": "tenant-a" } }
                    ]
                }
            }),
            aggregations: json!({}),
            sort: Vec::new(),
            from: 0,
            size: 10,
        },
    )
}

fn repeat_search(engine: &TantivyEngine, request: SearchRequest) -> Duration {
    let started = Instant::now();
    for _ in 0..32 {
        let response = engine.search(request.clone()).unwrap();
        assert!(response.total_hits > 0);
        black_box(response);
    }
    started.elapsed()
}

fn seeded_engine() -> TantivyEngine {
    let engine = empty_engine();
    for id in 0..DOC_COUNT {
        index_document(&engine, id);
    }
    engine
        .refresh(RefreshRequest {
            indices: vec![INDEX.to_string()],
        })
        .unwrap();
    engine
}

fn empty_engine() -> TantivyEngine {
    let engine = TantivyEngine::default();
    engine
        .create_index(CreateIndexRequest {
            index: INDEX.to_string(),
            settings: json!({}),
            mappings: json!({
                "properties": {
                    "message": { "type": "text" },
                    "service": { "type": "keyword" },
                    "tenant": { "type": "keyword" },
                    "latency": { "type": "long" },
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 3,
                        "space_type": "l2"
                    }
                }
            }),
        })
        .unwrap();
    engine
}

fn index_document(engine: &TantivyEngine, id: usize) {
    engine.index_document(document_request(id)).unwrap();
}

fn document_request(id: usize) -> IndexDocumentRequest {
    IndexDocumentRequest {
        index: INDEX.to_string(),
        id: format!("doc-{id:04}"),
        source: json!({
            "message": if id % 2 == 0 { "alpha latency" } else { "beta throughput" },
            "service": format!("svc-{}", id % 4),
            "tenant": if id % 3 == 0 { "tenant-a" } else { "tenant-b" },
            "latency": (id % 17) as u64,
            "embedding": [
                (id % 11) as f32 / 10.0,
                (id % 7) as f32 / 10.0,
                (id % 5) as f32 / 10.0
            ]
        }),
    }
}

fn record(name: &str, operations: usize, elapsed: Duration) {
    println!(
        "{}",
        json!({
            "benchmark": name,
            "operations": operations,
            "elapsed_nanos": elapsed.as_nanos(),
            "nanos_per_operation": elapsed.as_nanos() / operations as u128
        })
    );
}
