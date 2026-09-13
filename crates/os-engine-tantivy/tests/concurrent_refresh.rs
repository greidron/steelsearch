use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{mpsc, Arc, Barrier};
use std::time::Duration;

use os_engine::{
    CreateIndexRequest, DeleteDocumentRequest, IndexDocumentRequest, IndexEngine, RefreshRequest,
    SearchRequest, SearchResponse,
};
use os_engine_tantivy::TantivyEngine;
use serde_json::json;

fn search_documents(engine: &TantivyEngine) -> SearchResponse {
    engine
        .search(SearchRequest {
            indices: vec!["concurrent-refresh".to_string()],
            query: json!({"match_all": {}}),
            aggregations: json!({}),
            sort: vec![],
            from: 0,
            size: 128,
            stored_fields: None,
            source_fields: None,
            source_filter: None,
            source_includes: None,
            source_include: None,
            source_excludes: None,
            source_exclude: None,
            highlight: None,
            explain: false,
        })
        .unwrap()
}

fn check_concurrent_refresh(shards: u32, overwrite_delete: bool) {
    const WORKERS: usize = 8;
    const WRITES: usize = 3;
    for round in 0..12 {
        let engine = Arc::new(TantivyEngine::default());
        engine
            .create_index(CreateIndexRequest {
                index: "concurrent-refresh".to_string(),
                settings: json!({"number_of_shards": shards}),
                mappings: json!({"properties": {"@timestamp": {"type": "date"}}}),
            })
            .unwrap();
        if overwrite_delete {
            for worker in 0..WORKERS {
                engine
                    .index_document(IndexDocumentRequest {
                        index: "concurrent-refresh".to_string(),
                        id: worker.to_string(),
                        source: json!({"completed": false, "task": {"id": worker.to_string()},
                        "response": {"created": 0}}),
                    })
                    .unwrap();
            }
            engine
                .refresh(RefreshRequest {
                    indices: vec!["concurrent-refresh".to_string()],
                })
                .unwrap();
        }
        let barrier = Arc::new(Barrier::new(WORKERS));
        let (sender, receiver) = mpsc::channel();
        let mut workers = Vec::new();
        for worker in 0..WORKERS {
            let engine = Arc::clone(&engine);
            let barrier = Arc::clone(&barrier);
            let sender = sender.clone();
            workers.push(std::thread::spawn(move || {
                barrier.wait();
                for write in 0..WRITES {
                    let id = if overwrite_delete {
                        worker.to_string()
                    } else {
                        format!("{worker}-{write}")
                    };
                    engine
                        .index_document(IndexDocumentRequest {
                            index: "concurrent-refresh".to_string(),
                            id: id.clone(),
                            source: json!({"completed": true, "task": {"id": id},
                            "response": {"created": worker + 1, "revision": write}}),
                        })
                        .unwrap();
                    engine
                        .refresh(RefreshRequest {
                            indices: vec!["concurrent-refresh".to_string()],
                        })
                        .unwrap();
                }
                if overwrite_delete && worker % 2 == 0 {
                    engine
                        .delete_document(DeleteDocumentRequest {
                            index: "concurrent-refresh".to_string(),
                            id: worker.to_string(),
                        })
                        .unwrap();
                    engine
                        .refresh(RefreshRequest {
                            indices: vec!["concurrent-refresh".to_string()],
                        })
                        .unwrap();
                }
                sender.send(()).unwrap();
            }));
        }
        drop(sender);
        for _ in 0..WORKERS {
            receiver
                .recv_timeout(Duration::from_secs(10))
                .unwrap_or_else(|error| {
                    panic!("refresh did not finish: shards={shards}, round={round}, {error}")
                });
        }
        for worker in workers {
            worker.join().unwrap();
        }
        let response = search_documents(&engine);
        let mut ids = response
            .hits
            .iter()
            .map(|hit| hit.metadata.id.clone())
            .collect::<Vec<_>>();
        ids.sort();
        let mut expected = if overwrite_delete {
            (0..WORKERS)
                .filter(|worker| worker % 2 != 0)
                .map(|worker| worker.to_string())
                .collect::<Vec<_>>()
        } else {
            (0..WORKERS)
                .flat_map(|worker| (0..WRITES).map(move |write| format!("{worker}-{write}")))
                .collect::<Vec<_>>()
        };
        expected.sort();
        assert_eq!(
            response.total_hits,
            expected.len() as u64,
            "shards={shards}, round={round}, returned IDs={ids:?}"
        );
        assert_eq!(ids, expected, "shards={shards}, round={round}");
        if overwrite_delete {
            for hit in &response.hits {
                let worker = hit.metadata.id.parse::<usize>().unwrap();
                assert_eq!(
                    hit.source,
                    json!({"completed": true, "task": {"id": worker.to_string()},
                    "response": {"created": worker + 1, "revision": WRITES - 1}}),
                    "stale source: shards={shards}, round={round}, id={worker}"
                );
            }
        }
    }
}

#[test]
fn concurrent_single_shard_refresh_has_exactly_one_hit_per_document() {
    check_concurrent_refresh(1, false);
}

#[test]
fn concurrent_three_shard_refresh_completes_without_duplicate_hits() {
    check_concurrent_refresh(3, false);
}

#[test]
fn concurrent_single_shard_refresh_preserves_overwrites_and_deletions() {
    check_concurrent_refresh(1, true);
}

#[test]
fn concurrent_three_shard_refresh_preserves_overwrites_and_deletions() {
    check_concurrent_refresh(3, true);
}

fn check_search_during_refresh(shards: u32) {
    const READERS: usize = 4;
    const DOCUMENTS: usize = 64;
    for round in 0..3 {
        let engine = Arc::new(TantivyEngine::default());
        engine
            .create_index(CreateIndexRequest {
                index: "concurrent-refresh".to_string(),
                settings: json!({"number_of_shards": shards}),
                mappings: json!({"properties": {"ordinal": {"type": "integer"}}}),
            })
            .unwrap();
        let finished = Arc::new(AtomicBool::new(false));
        let barrier = Arc::new(Barrier::new(READERS + 1));
        let (sender, receiver) = mpsc::channel();
        let mut workers = Vec::new();
        for reader in 0..READERS {
            let engine = Arc::clone(&engine);
            let finished = Arc::clone(&finished);
            let barrier = Arc::clone(&barrier);
            let sender = sender.clone();
            workers.push(std::thread::spawn(move || {
                barrier.wait();
                loop {
                    let response = search_documents(&engine);
                    assert_eq!(
                        response.total_hits as usize,
                        response.hits.len(),
                        "count/hit mismatch: shards={shards}, round={round}, reader={reader}"
                    );
                    let mut ids = std::collections::BTreeSet::new();
                    for hit in &response.hits {
                        assert!(
                            ids.insert(hit.metadata.id.clone()),
                            "duplicate hit during refresh"
                        );
                        let ordinal = hit.metadata.id.parse::<usize>().unwrap();
                        assert_eq!(
                            hit.source,
                            json!({"ordinal": ordinal}),
                            "source/ID mismatch during refresh"
                        );
                    }
                    if finished.load(Ordering::Acquire) {
                        break;
                    }
                    std::thread::yield_now();
                }
                sender.send(()).unwrap();
            }));
        }
        let writer_engine = Arc::clone(&engine);
        let writer_sender = sender.clone();
        workers.push(std::thread::spawn(move || {
            barrier.wait();
            for ordinal in 0..DOCUMENTS {
                writer_engine
                    .index_document(IndexDocumentRequest {
                        index: "concurrent-refresh".to_string(),
                        id: ordinal.to_string(),
                        source: json!({"ordinal": ordinal}),
                    })
                    .unwrap();
                writer_engine
                    .refresh(RefreshRequest {
                        indices: vec!["concurrent-refresh".to_string()],
                    })
                    .unwrap();
            }
            finished.store(true, Ordering::Release);
            writer_sender.send(()).unwrap();
        }));
        drop(sender);
        for _ in 0..=READERS {
            receiver.recv_timeout(Duration::from_secs(30))
                .unwrap_or_else(|error| panic!("concurrent search/refresh did not finish: shards={shards}, round={round}, {error}"));
        }
        for worker in workers {
            worker.join().unwrap();
        }
        let final_response = search_documents(&engine);
        assert_eq!(final_response.total_hits, DOCUMENTS as u64);
        assert_eq!(final_response.hits.len(), DOCUMENTS);
    }
}

#[test]
fn single_shard_search_observes_consistent_hits_during_refresh() {
    check_search_during_refresh(1);
}

#[test]
fn three_shard_search_observes_consistent_hits_during_refresh() {
    check_search_during_refresh(3);
}

#[test]
fn overwrite_and_delete_keep_the_published_view_until_refresh() {
    for shards in [1, 3] {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "concurrent-refresh".to_string(),
                settings: json!({"number_of_shards": shards}),
                mappings: json!({"properties": {"revision": {"type": "integer"}}}),
            })
            .unwrap();
        for id in ["a", "b"] {
            engine
                .index_document(IndexDocumentRequest {
                    index: "concurrent-refresh".to_string(),
                    id: id.to_string(),
                    source: json!({"revision": 0}),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["concurrent-refresh".to_string()],
            })
            .unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "concurrent-refresh".to_string(),
                id: "a".to_string(),
                source: json!({"revision": 1}),
            })
            .unwrap();
        engine
            .delete_document(DeleteDocumentRequest {
                index: "concurrent-refresh".to_string(),
                id: "b".to_string(),
            })
            .unwrap();
        let before = search_documents(&engine);
        assert_eq!(
            before.total_hits, 2,
            "pending writes changed the published count: shards={shards}"
        );
        let mut ids = before
            .hits
            .iter()
            .map(|hit| hit.metadata.id.as_str())
            .collect::<Vec<_>>();
        ids.sort();
        assert_eq!(ids, vec!["a", "b"]);
        for hit in before.hits {
            assert_eq!(
                hit.source,
                json!({"revision": 0}),
                "pending overwrite leaked: shards={shards}"
            );
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["concurrent-refresh".to_string()],
            })
            .unwrap();
        let after = search_documents(&engine);
        assert_eq!(
            after.total_hits, 1,
            "deleted document survived refresh: shards={shards}"
        );
        assert_eq!(after.hits.len(), 1);
        assert_eq!(after.hits[0].metadata.id, "a");
        assert_eq!(after.hits[0].source, json!({"revision": 1}));
    }
}
