use super::*;
use serde_json::json;

fn read(engine: &TantivyEngine, routing: Option<&str>) -> Option<GetDocumentResponse> {
    engine.get_refreshed_document_with_routing(
        GetDocumentRequest { index: "published".into(), id: "same".into() }, routing,
    ).unwrap()
}

fn create(shards: u32) -> TantivyEngine {
    let engine = TantivyEngine::default();
    engine.create_index(CreateIndexRequest {
        index: "published".into(), settings: json!({"number_of_shards": shards}),
        mappings: json!({"properties": {"body": {"type": "text"}}}),
    }).unwrap();
    engine
}

fn refresh(engine: &TantivyEngine) {
    engine.refresh(RefreshRequest { indices: vec!["published".into()] }).unwrap();
}

fn assert_late_replay_survives_persistence(per_shard: bool, replacement: bool) {
    let request = CreateIndexRequest {
        index: "published".into(), settings: json!({"number_of_shards": 1}),
        mappings: json!({"properties": {"body": {"type": "text"}}}),
    };
    let schema = map_opensearch_index_to_tantivy_schema(&request).unwrap();
    let engine = TantivyEngine::default();
    engine.create_index(request).unwrap();
    let path = std::env::temp_dir().join(format!(
        "late-replay-{}-{per_shard}-{replacement}-{}",
        std::process::id(),
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos(),
    ));
    let replay = |id: &str, seq_no, version, body: &str| {
        engine.replay_document_with_routing(ReplayDocumentRequest {
            index: "published".into(),
            metadata: DocumentMetadata { id: id.into(), version, seq_no, primary_term: 1 },
            coordination: WriteCoordinationMetadata::default(), source: json!({"body": body}),
        }, Some("tenant")).unwrap();
    };
    let second_path = path.join("second");
    let persist = |path: &Path| {
        if per_shard {
            engine.persist_index_shard_state("published", 0, path)
        } else {
            engine.persist_shard_state("published", path)
        }
    };
    if replacement {
        replay("same", 1, 1, "old");
    }
    replay("newer", 9, 1, "newer");
    persist(&path).unwrap();
    persist(&second_path).unwrap();
    replay("same", 3, 2, "late");
    for destination in [&path, &second_path] {
        persist(destination).unwrap();
        let recovered = TantivyEngine::default();
        recovered.recover_index_from_manifest("published", schema.clone(), destination).unwrap();
        refresh(&recovered);
        let actual = read(&recovered, Some("tenant")).expect("late replay must survive restart");
        assert_eq!(actual.metadata.seq_no, 3);
        assert_eq!(actual.metadata.version, 2);
        assert_eq!(actual.source, json!({"body": "late"}));
    }
    // A normal replacement after the late replay must return to incremental append.
    replay("same", 10, 3, "ordered");
    for destination in [&path, &second_path] {
        persist(destination).unwrap();
        assert_eq!(fs::read_to_string(operations_path(destination)).unwrap().lines().count(), 3);
    }
    replay("same", 11, 4, "retry");
    let manifest_temp = ShardManifest::manifest_path(&path).with_extension("json.tmp");
    fs::create_dir(&manifest_temp).unwrap();
    assert!(persist(&path).is_err());
    fs::remove_dir(&manifest_temp).unwrap();
    persist(&path).unwrap();
    assert_eq!(fs::read_to_string(operations_path(&path)).unwrap().lines().count(), 2);
    let recovered = TantivyEngine::default();
    recovered.recover_index_from_manifest("published", schema.clone(), &path).unwrap();
    refresh(&recovered);
    assert_eq!(read(&recovered, Some("tenant")).unwrap().metadata.seq_no, 11);
    engine.delete_document_with_routing(DeleteDocumentRequest {
        index: "published".into(), id: "same".into(),
    }, Some("tenant")).unwrap();
    for destination in [&path, &second_path] {
        persist(destination).unwrap();
        let recovered = TantivyEngine::default();
        recovered.recover_index_from_manifest("published", schema.clone(), destination).unwrap();
        refresh(&recovered);
        assert!(read(&recovered, Some("tenant")).is_none());
        assert_eq!(fs::read_to_string(operations_path(destination)).unwrap().lines().count(), 1);
    }
    fs::remove_dir_all(&path).unwrap();
}

#[test]
fn late_replay_insert_survives_index_persistence() {
    assert_late_replay_survives_persistence(false, false);
}

fn assert_write_during_persistence_is_not_acknowledged_early(per_shard: bool) {
    for action in ["insert", "replace", "delete"] {
        let request = CreateIndexRequest {
            index: "published".into(), settings: json!({"number_of_shards": 1}),
            mappings: json!({"properties": {"body": {"type": "text"}}}),
        };
        let schema = map_opensearch_index_to_tantivy_schema(&request).unwrap();
        let engine = TantivyEngine::default();
        engine.create_index(request).unwrap();
        let path = std::env::temp_dir().join(format!(
            "persistence-interleaving-{}-{per_shard}-{action}-{}", std::process::id(),
            std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos(),
        ));
        let replay = |id: &str, seq_no, body: &str| {
            engine.replay_document_with_routing(ReplayDocumentRequest {
                index: "published".into(),
                metadata: DocumentMetadata { id: id.into(), version: 1, seq_no, primary_term: 1 },
                coordination: WriteCoordinationMetadata::default(), source: json!({"body": body}),
            }, Some("tenant")).unwrap();
        };
        let recover = || {
            let recovered = TantivyEngine::default();
            recovered.recover_index_from_manifest("published", schema.clone(), &path).unwrap();
            refresh(&recovered);
            read(&recovered, Some("tenant"))
        };
        if action != "insert" {
            replay("same", 1, "old");
        }
        replay("newer", 9, "newer");
        let shard_id = per_shard.then_some(0);
        engine.persist_document_state("published", shard_id, &path).unwrap();
        let before = recover();
        engine.persist_document_state_after_snapshot("published", shard_id, &path, || {
            // Joining the writer also checks that snapshot capture released the store lock.
            std::thread::scope(|scope| {
                scope.spawn(|| {
                    if action == "delete" {
                        engine.delete_document_with_routing(DeleteDocumentRequest {
                            index: "published".into(), id: "same".into(),
                        }, Some("tenant")).unwrap();
                    } else {
                        replay("same", 3, "late");
                    }
                }).join().unwrap();
            });
        }).unwrap();
        assert_eq!(recover(), before, "first save must contain its captured snapshot: {action}");
        engine.persist_document_state("published", shard_id, &path).unwrap();
        let after = recover();
        fs::remove_dir_all(&path).unwrap();
        if action == "delete" {
            assert!(after.is_none());
        } else {
            let after = after.expect("write during previous save must be persisted next time");
            assert_eq!(after.metadata.seq_no, 3);
            assert_eq!(after.source, json!({"body": "late"}));
        }
    }
}

#[test]
fn writes_during_index_persistence_survive_the_next_save() {
    assert_write_during_persistence_is_not_acknowledged_early(false);
}

#[test]
fn writes_during_shard_persistence_survive_the_next_save() {
    assert_write_during_persistence_is_not_acknowledged_early(true);
}

#[test]
fn late_replay_replacement_survives_index_persistence() {
    assert_late_replay_survives_persistence(false, true);
}

#[test]
fn late_replay_insert_survives_shard_persistence() {
    assert_late_replay_survives_persistence(true, false);
}

#[test]
fn late_replay_replacement_survives_shard_persistence() {
    assert_late_replay_survives_persistence(true, true);
}

#[test]
fn late_replay_in_another_shard_invalidates_index_checkpoint() {
    let engine = create(3);
    let routes = {
        let store = engine.store.read().unwrap();
        let documents = &store.indices["published"].documents;
        let mut routes = BTreeMap::new();
        for number in 0..100 {
            let route = format!("tenant-{number}");
            routes.entry(documents.shard_id_for_write("same", Some(&route))).or_insert(route);
        }
        routes.into_values().collect::<Vec<_>>()
    };
    assert_eq!(routes.len(), 3);
    let path = std::env::temp_dir().join(format!(
        "late-replay-cross-shard-{}-{}", std::process::id(),
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos(),
    ));
    for (ordinal, (id, seq_no)) in [("newer", 9), ("same", 3)].into_iter().enumerate() {
        engine.replay_document_with_routing(ReplayDocumentRequest {
            index: "published".into(),
            metadata: DocumentMetadata { id: id.into(), version: 1, seq_no, primary_term: 1 },
            coordination: WriteCoordinationMetadata::default(), source: json!({"body": id}),
        }, Some(&routes[ordinal])).unwrap();
        engine.persist_shard_state("published", &path).unwrap();
    }
    let manifest = load_shard_manifest(&path).unwrap();
    let operations = replay_operations(&path, &manifest).unwrap();
    fs::remove_dir_all(&path).unwrap();
    assert_eq!(operations.len(), 2);
    assert_eq!(operations["same"].metadata.seq_no, 3);
    assert_eq!(operations["same"].routing.as_ref(), Some(&routes[1]));
}

#[test]
fn late_replay_is_not_lost_behind_the_refresh_watermark() {
    for shards in [1, 3] {
        let engine = create(shards);
        let mut old = None;
        for (id, seq_no) in [("newer", 9), ("same", 3)] {
            engine.replay_document_with_routing(ReplayDocumentRequest {
                index: "published".into(),
                metadata: DocumentMetadata { id: id.into(), version: 1, seq_no, primary_term: 1 },
                coordination: WriteCoordinationMetadata::default(), source: json!({"body": id}),
            }, Some("tenant")).unwrap();
            assert!(read(&engine, Some("tenant")).is_none());
            refresh(&engine);
            if id == "newer" {
                let store = engine.store.read().unwrap();
                let index = &store.indices["published"];
                let shard = index.documents.shard_id_for_write("same", Some("tenant"));
                assert_eq!(index.opensearch_bm25_field_stats("body", shard).unwrap().doc_count, 1);
                old = Some((Arc::clone(&index.bm25_stats_cache), shard));
            }
        }
        let late = read(&engine, Some("tenant")).unwrap();
        assert_eq!(late.metadata.seq_no, 3);
        assert_eq!(late.source, json!({"body": "same"}));
        assert!(engine.get_refreshed_document_with_routing(GetDocumentRequest {
            index: "published".into(), id: "newer".into(),
        }, Some("tenant")).unwrap().is_some());
        let (old, shard) = old.unwrap();
        assert_eq!(engine.store.read().unwrap().indices["published"]
            .opensearch_bm25_field_stats("body", shard).unwrap().doc_count, 2);
        assert_eq!(old.lock().unwrap()[&shard]["body"].doc_count, 1);
    }
}

#[test]
fn published_document_lookup_preserves_versions_across_pending_mutations() {
    for shards in [1, 3] {
        let engine = create(shards);
        assert!(read(&engine, Some("tenant")).is_none());
        for (seq_no, version, text) in [(0, 0, "zero"), (1, 7, "first"), (2, 42, "replacement")] {
            let old = read(&engine, Some("tenant"));
            let metadata = DocumentMetadata {
                id: "same".into(), version, seq_no, primary_term: 3,
            };
            engine.replay_document_with_routing(ReplayDocumentRequest {
                index: "published".into(), metadata: metadata.clone(),
                coordination: WriteCoordinationMetadata::default(), source: json!({"body": text}),
            }, Some("tenant")).unwrap();
            assert_eq!(read(&engine, Some("tenant")), old);
            refresh(&engine);
            let published = read(&engine, Some("tenant")).unwrap();
            assert_eq!(published.metadata, metadata);
            assert_eq!(published.source, json!({"body": text}));
        }
        let old = read(&engine, Some("tenant"));
        engine.delete_document_with_routing(DeleteDocumentRequest {
            index: "published".into(), id: "same".into(),
        }, Some("tenant")).unwrap();
        assert_eq!(read(&engine, Some("tenant")), old);
        refresh(&engine);
        assert!(read(&engine, Some("tenant")).is_none());
        // Returned values remain owned snapshots after their source document is deleted.
        assert_eq!(old.unwrap().metadata.version, 42);
    }
}

#[test]
fn published_document_lookup_uses_routing_shard_not_all_shards() {
    let engine = create(3);
    let mut routes = BTreeMap::new();
    {
        let store = engine.store.read().unwrap();
        let documents = &store.indices["published"].documents;
        for number in 0..100 {
            let route = format!("tenant-{number}");
            routes.entry(documents.shard_id_for_write("same", Some(&route))).or_insert(route);
        }
    }
    assert_eq!(routes.len(), 3);
    for route in routes.values() {
        engine.index_document_with_routing(IndexDocumentRequest {
            index: "published".into(), id: "same".into(), source: json!({"body": route}),
        }, Some(route)).unwrap();
    }
    refresh(&engine);
    for route in routes.values() {
        assert_eq!(read(&engine, Some(route)).unwrap().source, json!({"body": route}));
    }
    let default_shard = engine.store.read().unwrap().indices["published"]
        .documents.shard_id_for_write("same", None);
    assert_eq!(read(&engine, None).unwrap().source, json!({"body": routes[&default_shard]}));
    let removed_route = routes.values().next().unwrap();
    engine.delete_document_with_routing(DeleteDocumentRequest {
        index: "published".into(), id: "same".into(),
    }, Some(removed_route)).unwrap();
    refresh(&engine);
    assert!(read(&engine, Some(removed_route)).is_none());
    for route in routes.values().filter(|route| *route != removed_route) {
        assert_eq!(read(&engine, Some(route)).unwrap().source, json!({"body": route}));
    }
    assert!(matches!(engine.get_refreshed_document_with_routing(
        GetDocumentRequest { index: "missing".into(), id: "same".into() }, None,
    ), Err(EngineError::IndexNotFound { .. })));
}
