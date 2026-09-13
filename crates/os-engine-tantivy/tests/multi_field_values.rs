use os_engine::{CreateIndexRequest, IndexDocumentRequest, IndexEngine, RefreshRequest};
use os_engine_tantivy::{map_opensearch_index_to_tantivy_schema, MultiFieldSource, TantivyEngine};
use serde_json::{json, Value};

fn descriptor() -> MultiFieldSource {
    let schema = map_opensearch_index_to_tantivy_schema(&CreateIndexRequest {
        index: "multi-values".to_string(),
        settings: json!({}),
        mappings: json!({"properties": {"object": {"properties": {
            "value": {"type": "text", "fields": {
                "raw": {"type": "keyword", "ignore_above": 2, "fields": {
                    "exact": {"type": "keyword", "ignore_above": 4}
                }}
            }}
        }}}}),
    })
    .unwrap();
    schema
        .fields
        .into_iter()
        .find(|field| field.name == "object.value.raw.exact")
        .unwrap()
        .multi_field_source
        .unwrap()
}

#[test]
fn multi_field_values_public_api_uses_root_parent_and_child_options() {
    let descriptor = descriptor();
    assert_eq!(descriptor.path, "object.value");
    assert_eq!(descriptor.ignore_above, Some(4));
    let source = json!({"object": [
        {"value": ["Beta", null, [12, true], "abcde"]},
        {"value": "\u{1f600}\u{1f600}"},
        {"value": "\u{1f600}\u{1f600}a"},
        {"unrelated": "value"}
    ], "object.value.raw.exact": "fake", "value": "fake"});
    let original = source.clone();
    assert_eq!(
        descriptor.keyword_values(&source).unwrap(),
        vec![
            json!("Beta"),
            json!("12"),
            json!("true"),
            json!("\u{1f600}\u{1f600}")
        ]
    );
    assert_eq!(source, original);
}

#[test]
fn multi_field_values_public_api_distinguishes_errors_from_absence() {
    let descriptor = descriptor();
    for source in [
        json!({}),
        json!({"object": {"value": null}}),
        json!({"object": {"value": [null, "too long"]}}),
    ] {
        assert!(descriptor.keyword_values(&source).unwrap().is_empty());
    }
    let source = json!({"object": {"value": ["ok", {"invalid": true}]}});
    assert!(descriptor.keyword_values(&source).is_err());
    let normalized = MultiFieldSource {
        normalizer: Some("casefold".to_string()),
        ..descriptor
    };
    assert!(normalized
        .keyword_values(&json!({"object": {"value": "Beta"}}))
        .is_err());
    assert!(normalized.keyword_values(&Value::Null).is_err());
}

#[test]
fn multi_field_values_mapping_lookup_does_not_confuse_objects_or_leaf_names() {
    let mappings = json!({"properties": {
        "value": {"type": "text", "fields": {"raw": {"type": "keyword", "ignore_above": 4}}},
        "object": {"properties": {"raw": {"type": "keyword"},
            "value": {"type": "text", "fields": {"raw": {"type": "keyword", "fields": {
                "exact": {"type": "keyword", "ignore_above": "8"}
            }}}}
        }}
    }});
    for field in [
        "raw",
        "object.raw",
        "missing.raw",
        "value.absent",
        "object.value",
    ] {
        assert_eq!(
            MultiFieldSource::for_keyword_field(&mappings, field).unwrap(),
            None,
            "{field}"
        );
    }
    assert_eq!(
        MultiFieldSource::for_keyword_field(&mappings, "value.raw").unwrap(),
        Some(MultiFieldSource {
            path: "value".to_string(),
            ignore_above: Some(4),
            normalizer: None
        })
    );
    assert_eq!(
        MultiFieldSource::for_keyword_field(&mappings, "object.value.raw.exact").unwrap(),
        Some(MultiFieldSource {
            path: "object.value".to_string(),
            ignore_above: Some(8),
            normalizer: None
        })
    );
}

#[test]
fn multi_field_public_engine_sort_pages_use_parent_values() {
    check_multi_field_engine_sort_pages(false);
}

#[test]
fn multi_field_public_engine_filtered_sort_pages_use_parent_values() {
    check_multi_field_engine_sort_pages(true);
}

#[test]
fn multi_field_replayed_dynamic_documents_preserve_keyword_sort_pages() {
    use os_engine::{DocumentMetadata, ReplayDocumentRequest, WriteCoordinationMetadata};

    for shards in [1, 3] {
        let engine = TantivyEngine::default();
        engine.create_index(CreateIndexRequest {
            index: "replayed-dynamic".to_string(),
            settings: json!({"number_of_shards": shards}),
            mappings: json!({}),
        }).unwrap();
        for (seq_no, id, value) in [(0, "one", "seed"), (1, "two", "good")] {
            engine.replay_document_with_routing(ReplayDocumentRequest {
                index: "replayed-dynamic".to_string(),
                metadata: DocumentMetadata {
                    id: id.to_string(), version: 1, seq_no, primary_term: 1,
                },
                coordination: WriteCoordinationMetadata::default(),
                source: json!({"value": value}),
            }, None).unwrap();
        }
        engine.refresh(RefreshRequest { indices: vec!["replayed-dynamic".to_string()] }).unwrap();
        for (order, expected) in [
            ("asc", [("two", "good"), ("one", "seed")]),
            ("desc", [("one", "seed"), ("two", "good")]),
        ] {
            for (offset, (id, value)) in expected.into_iter().enumerate() {
                let response = engine.search(serde_json::from_value(json!({
                    "indices": ["replayed-dynamic"], "query": {"match_all": {}},
                    "aggregations": {}, "sort": [{"field": "value.keyword", "order": order}],
                    "from": offset, "size": 1
                })).unwrap()).unwrap();
                assert_eq!(response.total_hits, 2);
                assert_eq!(response.hits[0].metadata.id, id, "{shards} shards, {order}, {offset}");
                assert_eq!(response.hits[0].sort, Some(json!([value])));
                assert_eq!(response.hits[0].source, json!({"value": value}));
            }
        }
    }
}

#[test]
fn multi_field_exists_sort_pages_use_filtered_parent_values() {
    for shards in [1, 3] {
        let engine = TantivyEngine::default();
        engine.create_index(CreateIndexRequest {
            index: "exists-sort".to_string(),
            settings: json!({"number_of_shards": shards}),
            mappings: json!({"properties": {"value": {"type": "text", "fields": {
                "raw": {"type": "keyword", "ignore_above": 8}
            }}}}),
        }).unwrap();
        for (id, value) in [
            ("a", json!("zulu")), ("z", json!("alpha")),
            ("array", json!(["beta", "Alpha", null])),
            ("missing", json!([null, "ignored long value"])),
        ] {
            engine.index_document(IndexDocumentRequest {
                index: "exists-sort".to_string(), id: id.to_string(), source: json!({"value": value}),
            }).unwrap();
        }
        engine.refresh(RefreshRequest { indices: vec!["exists-sort".to_string()] }).unwrap();
        for query in [
            json!({"exists": {"field": "value.raw"}}),
            json!({"bool": {"must": [{"match_all": {}}], "filter": [{"exists": {"field": "value.raw"}}]}}),
        ] {
            for (order, expected) in [
                ("asc", [("array", "Alpha"), ("z", "alpha"), ("a", "zulu")]),
                ("desc", [("a", "zulu"), ("array", "beta"), ("z", "alpha")]),
            ] {
                for (offset, (id, value)) in expected.into_iter().enumerate() {
                    let response = engine.search(serde_json::from_value(json!({
                        "indices": ["exists-sort"], "query": query,
                        "aggregations": {}, "sort": [{"field": "value.raw", "order": order}],
                        "from": offset, "size": 1
                    })).unwrap()).unwrap();
                    assert_eq!(response.total_hits, 3);
                    assert_eq!(response.hits[0].metadata.id, id, "{shards} shards, {order}, {offset}, {query}");
                    assert_eq!(response.hits[0].sort, Some(json!([value])));
                    assert_eq!(response.hits[0].source, match id {
                        "array" => json!({"value": ["beta", "Alpha", null]}),
                        _ => json!({"value": value}),
                    });
                }
            }
        }
    }
}

fn check_multi_field_engine_sort_pages(filtered: bool) {
    let engine = TantivyEngine::default();
    engine
        .create_index(CreateIndexRequest {
            index: "multi-sort".to_string(),
            settings: json!({"number_of_shards": 1}),
            mappings: json!({"properties": {"value": {"type": "text", "fields": {
                "raw": {"type": "keyword", "ignore_above": 8}
            }}}}),
        })
        .unwrap();
    for (id, value) in [("a", "zulu"), ("z", "alpha"), ("m", "beta")] {
        engine
            .index_document(IndexDocumentRequest {
                index: "multi-sort".to_string(),
                id: id.to_string(),
                source: json!({"value": value}),
            })
            .unwrap();
        engine
            .refresh(RefreshRequest {
                indices: vec!["multi-sort".to_string()],
            })
            .unwrap();
    }
    for (order, expected) in [
        ("asc", [("z", "alpha"), ("m", "beta"), ("a", "zulu")]),
        ("desc", [("a", "zulu"), ("m", "beta"), ("z", "alpha")]),
    ] {
        for (offset, (id, value)) in expected.into_iter().enumerate() {
            let query = if filtered {
                json!({"query": {"match_all": {}}, "post_filter": {"match_all": {}}})
            } else {
                json!({"match_all": {}})
            };
            let response = engine
                .search(
                    serde_json::from_value(json!({
                        "indices": ["multi-sort"], "query": query, "aggregations": {},
                        "sort": [{"field": "value.raw", "order": order}], "from": offset, "size": 1
                    }))
                    .unwrap(),
                )
                .unwrap();
            assert_eq!(response.total_hits, 3);
            assert_eq!(response.hits.len(), 1);
            assert_eq!(response.hits[0].metadata.id, id, "{order}, page {offset}");
            assert_eq!(response.hits[0].sort, Some(json!([value])));
            assert_eq!(response.hits[0].source, json!({"value": value}));
        }
    }
    if filtered {
        for (after, expected) in [("alpha", "m"), ("beta", "a")] {
            let response = engine.search(serde_json::from_value(json!({
                "indices": ["multi-sort"], "query": {"query": {"match_all": {}}, "search_after": [after]},
                "aggregations": {}, "sort": [{"field": "value.raw", "order": "asc"}], "from": 0, "size": 1
            })).unwrap()).unwrap();
            assert_eq!(response.total_hits, 3);
            assert_eq!(response.hits[0].metadata.id, expected);
        }
    }
}

#[test]
fn multi_field_filtered_sort_preserves_array_modes_and_missing_page_boundaries() {
    let engine = TantivyEngine::default();
    engine
        .create_index(CreateIndexRequest {
            index: "multi-missing".to_string(),
            settings: json!({}),
            mappings: json!({"properties": {"value": {"type": "text", "fields": {
                "raw": {"type": "keyword", "ignore_above": 8}
            }}}}),
        })
        .unwrap();
    for (id, value) in [
        ("a", json!(["alpha", "zulu"])),
        ("b", json!(["beta", null])),
        ("n", json!([null, "ignored long value"])),
    ] {
        engine
            .index_document(IndexDocumentRequest {
                index: "multi-missing".to_string(),
                id: id.to_string(),
                source: json!({"value": value}),
            })
            .unwrap();
    }
    engine
        .refresh(RefreshRequest {
            indices: vec!["multi-missing".to_string()],
        })
        .unwrap();
    for (order, mode, ids, values) in [
        ("asc", None, ["a", "b", "n"], json!(["alpha", "beta", null])),
        ("desc", None, ["a", "b", "n"], json!(["zulu", "beta", null])),
        (
            "asc",
            Some("max"),
            ["b", "a", "n"],
            json!(["beta", "zulu", null]),
        ),
        (
            "desc",
            Some("min"),
            ["b", "a", "n"],
            json!(["beta", "alpha", null]),
        ),
    ] {
        let sort = json!([{"field": "value.raw", "order": order, "mode": mode}]);
        let mut query = json!({"query": {"match_all": {}}, "post_filter": {"match_all": {}}});
        for (position, id) in ids.into_iter().enumerate() {
            let response = engine
                .search(
                    serde_json::from_value(json!({
                        "indices": ["multi-missing"], "query": query, "sort": sort,
                        "aggregations": {}, "from": 0, "size": 1
                    }))
                    .unwrap(),
                )
                .unwrap();
            assert_eq!(response.total_hits, 3);
            assert_eq!(response.hits.len(), 1);
            let hit = &response.hits[0];
            assert_eq!(hit.metadata.id, id, "{order}, {mode:?}, page {position}");
            assert_eq!(hit.sort, Some(json!([values[position]])));
            let original = match id {
                "a" => json!({"value": ["alpha", "zulu"]}),
                "b" => json!({"value": ["beta", null]}),
                _ => json!({"value": [null, "ignored long value"]}),
            };
            assert_eq!(hit.source, original);
            query["search_after"] = hit.sort.clone().unwrap();
        }
        let response = engine
            .search(
                serde_json::from_value(json!({
                    "indices": ["multi-missing"], "query": query, "sort": sort,
                    "aggregations": {}, "from": 0, "size": 1
                }))
                .unwrap(),
            )
            .unwrap();
        assert!(response.hits.is_empty());
    }
}

#[test]
fn multi_field_public_engine_sort_handles_shards_indices_and_secondary_keys() {
    for shards in [1, 3] {
        for index_count in [1, 2] {
            let engine = TantivyEngine::default();
            let indices = (0..index_count).map(|i| format!("multi-topology-{i}")).collect::<Vec<_>>();
            for index in &indices {
                engine.create_index(CreateIndexRequest {
                    index: index.clone(), settings: json!({"number_of_shards": shards}),
                    mappings: json!({"properties": {"value": {"type": "text", "fields": {
                        "raw": {"type": "keyword", "ignore_above": 8}
                    }}}}),
                }).unwrap();
            }
            for (position, (id, value)) in [("a", "zulu"), ("z", "alpha"), ("m", "beta")].into_iter().enumerate() {
                let index = &indices[position % index_count];
                engine.index_document(IndexDocumentRequest { index: index.clone(), id: id.to_string(),
                    source: json!({"value": value}) }).unwrap();
                engine.refresh(RefreshRequest { indices: vec![index.clone()] }).unwrap();
            }
            for secondary in [false, true] {
                for (order, expected) in [
                    ("asc", [("z", "alpha"), ("m", "beta"), ("a", "zulu")]),
                    ("desc", [("a", "zulu"), ("m", "beta"), ("z", "alpha")]),
                ] {
                    let mut sort = vec![json!({"field": "value.raw", "order": order})];
                    if secondary { sort.push(json!({"field": "_id", "order": "asc"})); }
                    for (offset, (id, value)) in expected.into_iter().enumerate() {
                        let response = engine.search(serde_json::from_value(json!({
                            "indices": indices, "query": {"match_all": {}}, "aggregations": {},
                            "sort": sort, "from": offset, "size": 1
                        })).unwrap()).unwrap();
                        assert_eq!(response.total_hits, 3);
                        assert_eq!(response.hits.len(), 1);
                        let hit = &response.hits[0];
                        assert_eq!(hit.metadata.id, id, "shards={shards}, indices={index_count}, secondary={secondary}, {order}, offset={offset}");
                        assert_eq!(hit.sort, Some(if secondary { json!([value, id]) } else { json!([value]) }));
                        assert_eq!(hit.source, json!({"value": value}));
                    }
                }
            }
        }
    }
}
