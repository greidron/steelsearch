use os_engine::{
    BulkWriteOperation, BulkWriteRequest, CreateIndexRequest, IndexDocumentRequest, IndexEngine,
    RefreshRequest, SearchRequest,
};
use os_engine_tantivy::TantivyEngine;
use serde_json::json;
use std::hint::black_box;
use std::time::{Duration, Instant};

const DOC_COUNT: usize = 128;
const NESTED_DOC_COUNT: usize = 4096;
const NESTED_CHILDREN_PER_DOC: usize = 8;
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
    record(
        "nested_child_index_search",
        64,
        benchmark_nested_child_index_search(),
    );
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
        search_request(json!({ "match": { "message": "alpha" } }), json!({})),
    )
}

fn benchmark_aggregation(engine: &TantivyEngine) -> Duration {
    repeat_search(
        engine,
        search_request(
            json!({ "match_all": {} }),
            json!({
                "by_service": {
                    "terms": {
                        "field": "service",
                        "size": 4
                    }
                }
            }),
        ),
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
        search_request(
            json!({
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
            json!({}),
        ),
    )
}

fn benchmark_nested_child_index_search() -> Duration {
    let engine = empty_engine();
    for id in 0..NESTED_DOC_COUNT {
        engine.index_document(nested_document_request(id)).unwrap();
    }
    engine
        .refresh(RefreshRequest {
            indices: vec![INDEX.to_string()],
        })
        .unwrap();

    let request = search_request(
        json!({
            "nested": {
                "path": "comments",
                "query": {
                    "bool": {
                        "must": [
                            { "term": { "comments.author": "alice" } },
                            { "term": { "comments.tag": "y" } }
                        ]
                    }
                }
            }
        }),
        json!({}),
    );

    let started = Instant::now();
    for _ in 0..64 {
        let response = engine.search(request.clone()).unwrap();
        assert_eq!(response.total_hits, (NESTED_DOC_COUNT / 16) as u64);
        black_box(response);
    }
    started.elapsed()
}

fn search_request(query: serde_json::Value, aggregations: serde_json::Value) -> SearchRequest {
    SearchRequest {
        indices: vec![INDEX.to_string()],
        query,
        aggregations,
        sort: Vec::new(),
        from: 0,
        size: 10,
        stored_fields: None,
        source_fields: None,
        source_filter: None,
        source_includes: None,
        source_include: None,
        source_excludes: None,
        source_exclude: None,
        highlight: None,
        explain: false,
    }
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
                    },
                    "comments": { "type": "object" }
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

fn nested_document_request(id: usize) -> IndexDocumentRequest {
    let mut comments = Vec::with_capacity(NESTED_CHILDREN_PER_DOC);
    for child in 0..NESTED_CHILDREN_PER_DOC {
        let matching_tuple = id % 16 == 0 && child == id % NESTED_CHILDREN_PER_DOC;
        let flatten_false_positive_left = id % 16 == 1 && child == 0;
        let flatten_false_positive_right = id % 16 == 1 && child == 1;
        comments.push(json!({
            "author": if matching_tuple || flatten_false_positive_left {
                "alice".to_string()
            } else if flatten_false_positive_right {
                "bob".to_string()
            } else {
                format!("author-{}", (id + child) % 257)
            },
            "tag": if matching_tuple || flatten_false_positive_right {
                "y".to_string()
            } else if flatten_false_positive_left {
                "x".to_string()
            } else {
                format!("tag-{}", (id * 31 + child) % 251)
            }
        }));
    }
    IndexDocumentRequest {
        index: INDEX.to_string(),
        id: format!("nested-doc-{id:05}"),
        source: json!({
            "message": "nested benchmark",
            "service": "nested",
            "tenant": "tenant-nested",
            "latency": (id % 17) as u64,
            "embedding": [0.1, 0.2, 0.3],
            "comments": comments
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
