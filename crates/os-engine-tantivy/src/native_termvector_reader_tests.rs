use super::*;
use serde_json::json;

fn create() -> TantivyEngine {
    let engine = TantivyEngine::default();
    engine
        .create_index(CreateIndexRequest {
            index: "termvectors".into(),
            settings: json!({"number_of_shards": 2}),
            mappings: json!({"properties": {
                "body": {"type": "text", "term_vector": "with_positions_offsets"}
            }}),
        })
        .unwrap();
    engine
}

fn routing_for_other_shard(engine: &TantivyEngine, id: &str, routing: &str) -> String {
    let store = engine.store.read().unwrap();
    let documents = &store.indices["termvectors"].documents;
    let shard = documents.shard_id_for_write(id, Some(routing));
    (0..100)
        .map(|number| format!("other-tenant-{number}"))
        .find(|candidate| documents.shard_id_for_write(id, Some(candidate)) != shard)
        .expect("two primary shards must have a route for the other shard")
}

fn options(fields: &[&str]) -> NativeTermVectorOptions {
    NativeTermVectorOptions {
        fields: Some(fields.iter().map(|field| (*field).to_owned()).collect()),
        per_field_analyzer: BTreeMap::new(),
        positions: true,
        offsets: true,
        field_statistics: true,
        term_statistics: true,
    }
}

fn read(
    engine: &TantivyEngine,
    id: &str,
    routing: Option<&str>,
    options: &NativeTermVectorOptions,
) -> Option<NativeTermVectorResponse> {
    engine
        .get_native_refreshed_termvectors(
            GetDocumentRequest {
                index: "termvectors".into(),
                id: id.into(),
            },
            routing,
            options,
        )
        .unwrap()
}

fn read_realtime(
    engine: &TantivyEngine,
    id: &str,
    routing: Option<&str>,
    options: &NativeTermVectorOptions,
) -> Option<NativeTermVectorResponse> {
    engine
        .get_native_termvectors(
            GetDocumentRequest {
                index: "termvectors".into(),
                id: id.into(),
            },
            routing,
            options,
            true,
        )
        .unwrap()
}

fn refresh(engine: &TantivyEngine) {
    engine
        .refresh(RefreshRequest {
            indices: vec!["termvectors".into()],
        })
        .unwrap();
}

#[test]
fn native_realtime_reader_forks_published_segments_without_mutating_external_writer() {
    let engine = create();
    let options = options(&["body"]);
    for (id, body) in [("first", "alpha"), ("second", "beta")] {
        engine
            .index_document_with_routing(
                IndexDocumentRequest {
                    index: "termvectors".into(),
                    id: id.into(),
                    source: json!({"body":body}),
                },
                Some("tenant-a"),
            )
            .unwrap();
    }
    refresh(&engine);
    let published = read(&engine, "first", Some("tenant-a"), &options).unwrap();
    engine
        .index_document_with_routing(
            IndexDocumentRequest {
                index: "termvectors".into(),
                id: "first".into(),
                source: json!({"body":"gamma"}),
            },
            Some("tenant-a"),
        )
        .unwrap();
    let realtime = read_realtime(&engine, "first", Some("tenant-a"), &options).unwrap();
    assert_eq!(realtime.document.metadata.version, 2);
    assert_eq!(realtime.fields["body"]["terms"]["gamma"]["term_freq"], 1);
    assert!(realtime.fields["body"]["terms"].get("alpha").is_none());
    assert_eq!(
        read(&engine, "first", Some("tenant-a"), &options)
            .unwrap()
            .fields,
        published.fields
    );
    refresh(&engine);
    assert_eq!(
        read(&engine, "first", Some("tenant-a"), &options)
            .unwrap()
            .fields["body"]["terms"],
        realtime.fields["body"]["terms"]
    );
}

#[test]
fn native_realtime_termvectors_follow_pending_routed_document_lifecycle() {
    let engine = create();
    let options = options(&["body"]);
    let routing = "tenant-a";
    let other_routing = routing_for_other_shard(&engine, "first", routing);

    for (id, source) in [
        ("first", json!({"body": "Café 😀 alpha alpha"})),
        ("second", json!({"body": "alpha beta"})),
    ] {
        engine
            .index_document_with_routing(
                IndexDocumentRequest {
                    index: "termvectors".into(),
                    id: id.into(),
                    source,
                },
                Some(routing),
            )
            .unwrap();
    }

    assert!(read(&engine, "first", Some(routing), &options).is_none());
    assert!(read_realtime(&engine, "first", Some(&other_routing), &options).is_none());

    let first = read_realtime(&engine, "first", Some(routing), &options).unwrap();
    assert_eq!(first.document.metadata.version, 1);
    assert_eq!(
        first.document.source,
        json!({"body": "Café 😀 alpha alpha"})
    );
    assert_eq!(
        first.fields["body"],
        json!({
            "field_statistics": {"doc_count": 2, "sum_doc_freq": 5, "sum_ttf": 6},
            "terms": {
                "alpha": {
                    "term_freq": 2,
                    "doc_freq": 2,
                    "ttf": 3,
                    "tokens": [
                        {"position": 2, "start_offset": 8, "end_offset": 13},
                        {"position": 3, "start_offset": 14, "end_offset": 19}
                    ]
                },
                "café": {
                    "term_freq": 1,
                    "doc_freq": 1,
                    "ttf": 1,
                    "tokens": [{"position": 0, "start_offset": 0, "end_offset": 4}]
                },
                "😀": {
                    "term_freq": 1,
                    "doc_freq": 1,
                    "ttf": 1,
                    "tokens": [{"position": 1, "start_offset": 5, "end_offset": 7}]
                }
            }
        })
    );

    let second = read_realtime(&engine, "second", Some(routing), &options).unwrap();
    assert_eq!(second.document.metadata.version, 1);
    assert_eq!(
        second.fields["body"],
        json!({
            "field_statistics": {"doc_count": 2, "sum_doc_freq": 5, "sum_ttf": 6},
            "terms": {
                "alpha": {
                    "term_freq": 1,
                    "doc_freq": 2,
                    "ttf": 3,
                    "tokens": [{"position": 0, "start_offset": 0, "end_offset": 5}]
                },
                "beta": {
                    "term_freq": 1,
                    "doc_freq": 1,
                    "ttf": 1,
                    "tokens": [{"position": 1, "start_offset": 6, "end_offset": 10}]
                }
            }
        })
    );
    let first_repeat = read_realtime(&engine, "first", Some(routing), &options).unwrap();
    assert_eq!(first_repeat.document.metadata, first.document.metadata);
    assert_eq!(first_repeat.document.source, first.document.source);
    assert_eq!(first_repeat.fields, first.fields);

    refresh(&engine);
    let published = read(&engine, "first", Some(routing), &options).unwrap();
    assert_eq!(published.document.metadata.version, 1);
    assert_eq!(
        published.document.source,
        json!({"body": "Café 😀 alpha alpha"})
    );

    engine
        .index_document_with_routing(
            IndexDocumentRequest {
                index: "termvectors".into(),
                id: "first".into(),
                source: json!({"body": "pending beta"}),
            },
            Some(routing),
        )
        .unwrap();
    let pending = read_realtime(&engine, "first", Some(routing), &options).unwrap();
    assert_eq!(pending.document.metadata.version, 2);
    assert_eq!(pending.document.source, json!({"body": "pending beta"}));
    assert_eq!(
        pending.fields["body"]["terms"],
        json!({
            "beta": {
                "term_freq": 1,
                "doc_freq": 2,
                "ttf": 2,
                "tokens": [{"position": 1, "start_offset": 8, "end_offset": 12}]
            },
            "pending": {
                "term_freq": 1,
                "doc_freq": 1,
                "ttf": 1,
                "tokens": [{"position": 0, "start_offset": 0, "end_offset": 7}]
            }
        })
    );
    let still_published = read(&engine, "first", Some(routing), &options).unwrap();
    assert_eq!(still_published.document.metadata.version, 1);
    assert_eq!(
        still_published.document.source,
        json!({"body": "Café 😀 alpha alpha"})
    );

    engine
        .delete_document_with_routing(
            DeleteDocumentRequest {
                index: "termvectors".into(),
                id: "first".into(),
            },
            Some(routing),
        )
        .unwrap();
    assert!(read_realtime(&engine, "first", Some(routing), &options).is_none());
    let retained = read(&engine, "first", Some(routing), &options).unwrap();
    assert_eq!(retained.document.metadata.version, 1);
    assert_eq!(
        retained.document.source,
        json!({"body": "Café 😀 alpha alpha"})
    );

    refresh(&engine);
    assert!(read(&engine, "first", Some(routing), &options).is_none());
}

#[test]
fn native_refreshed_termvectors_report_scalar_and_array_unicode_tokens() {
    let engine = create();
    for (id, source) in [
        ("accent", json!({"body": "Café beta"})),
        ("astral", json!({"body": "Alpha 😀 beta"})),
        ("array", json!({"body": ["Café", "😀 beta"]})),
    ] {
        engine
            .index_document_with_routing(
                IndexDocumentRequest {
                    index: "termvectors".into(),
                    id: id.into(),
                    source,
                },
                Some("tenant-a"),
            )
            .unwrap();
    }
    refresh(&engine);

    let options = options(&["body"]);
    let accent = read(&engine, "accent", Some("tenant-a"), &options).unwrap();
    assert_eq!(accent.document.source, json!({"body": "Café beta"}));
    assert_eq!(
        accent.fields["body"],
        json!({
            "field_statistics": {"doc_count": 3, "sum_doc_freq": 8, "sum_ttf": 8},
            "terms": {
                "beta": {
                    "term_freq": 1,
                    "doc_freq": 3,
                    "ttf": 3,
                    "tokens": [{"position": 1, "start_offset": 5, "end_offset": 9}]
                },
                "café": {
                    "term_freq": 1,
                    "doc_freq": 2,
                    "ttf": 2,
                    "tokens": [{"position": 0, "start_offset": 0, "end_offset": 4}]
                }
            }
        })
    );

    let astral = read(&engine, "astral", Some("tenant-a"), &options).unwrap();
    assert_eq!(
        astral.fields["body"]["terms"],
        json!({
            "alpha": {
                "term_freq": 1,
                "doc_freq": 1,
                "ttf": 1,
                "tokens": [{"position": 0, "start_offset": 0, "end_offset": 5}]
            },
            "beta": {
                "term_freq": 1,
                "doc_freq": 3,
                "ttf": 3,
                "tokens": [{"position": 2, "start_offset": 9, "end_offset": 13}]
            },
            "😀": {
                "term_freq": 1,
                "doc_freq": 2,
                "ttf": 2,
                "tokens": [{"position": 1, "start_offset": 6, "end_offset": 8}]
            }
        })
    );

    let array = read(&engine, "array", Some("tenant-a"), &options).unwrap();
    assert_eq!(
        array.fields["body"]["terms"],
        json!({
            "beta": {
                "term_freq": 1,
                "doc_freq": 3,
                "ttf": 3,
                "tokens": [{"position": 102, "start_offset": 8, "end_offset": 12}]
            },
            "café": {
                "term_freq": 1,
                "doc_freq": 2,
                "ttf": 2,
                "tokens": [{"position": 0, "start_offset": 0, "end_offset": 4}]
            },
            "😀": {
                "term_freq": 1,
                "doc_freq": 2,
                "ttf": 2,
                "tokens": [{"position": 101, "start_offset": 5, "end_offset": 7}]
            }
        })
    );
}

#[test]
fn native_refreshed_termvectors_omit_disabled_tokens_and_statistics() {
    let engine = create();
    engine
        .index_document_with_routing(
            IndexDocumentRequest {
                index: "termvectors".into(),
                id: "flags".into(),
                source: json!({"body": "alpha alpha beta"}),
            },
            Some("tenant-a"),
        )
        .unwrap();
    refresh(&engine);

    let default_options = NativeTermVectorOptions::default();
    assert!(default_options.fields.is_none());
    assert!(default_options.positions);
    assert!(default_options.offsets);
    assert!(default_options.field_statistics);
    assert!(!default_options.term_statistics);
    let options = NativeTermVectorOptions {
        fields: Some(["body".to_owned()].into_iter().collect()),
        per_field_analyzer: BTreeMap::new(),
        positions: false,
        offsets: false,
        field_statistics: false,
        term_statistics: false,
    };
    let response = read(&engine, "flags", Some("tenant-a"), &options).unwrap();
    assert_eq!(
        response.fields["body"],
        json!({
            "terms": {
                "alpha": {"term_freq": 2},
                "beta": {"term_freq": 1}
            }
        })
    );
}

#[test]
fn native_refreshed_termvectors_follow_published_routing_visibility() {
    let engine = create();
    let options = options(&["body"]);
    let routing = "tenant-a";
    let other_routing = routing_for_other_shard(&engine, "same", routing);
    let request = IndexDocumentRequest {
        index: "termvectors".into(),
        id: "same".into(),
        source: json!({"body": "published alpha"}),
    };
    engine
        .index_document_with_routing(request, Some(routing))
        .unwrap();

    assert!(read(&engine, "same", Some(routing), &options).is_none());
    assert!(read(&engine, "same", Some(&other_routing), &options).is_none());
    assert!(read(&engine, "missing", Some(routing), &options).is_none());

    refresh(&engine);
    let published = read(&engine, "same", Some(routing), &options).unwrap();
    assert_eq!(
        published.document.source,
        json!({"body": "published alpha"})
    );
    assert!(read(&engine, "same", Some(&other_routing), &options).is_none());

    engine
        .index_document_with_routing(
            IndexDocumentRequest {
                index: "termvectors".into(),
                id: "same".into(),
                source: json!({"body": "pending beta"}),
            },
            Some(routing),
        )
        .unwrap();
    let still_published = read(&engine, "same", Some(routing), &options).unwrap();
    assert_eq!(
        still_published.document.source,
        json!({"body": "published alpha"})
    );

    refresh(&engine);
    let refreshed = read(&engine, "same", Some(routing), &options).unwrap();
    assert_eq!(refreshed.document.source, json!({"body": "pending beta"}));
    assert_eq!(
        refreshed.fields["body"]["terms"],
        json!({
            "beta": {
                "term_freq": 1,
                "doc_freq": 1,
                "ttf": 1,
                "tokens": [{"position": 1, "start_offset": 8, "end_offset": 12}]
            },
            "pending": {
                "term_freq": 1,
                "doc_freq": 1,
                "ttf": 1,
                "tokens": [{"position": 0, "start_offset": 0, "end_offset": 7}]
            }
        })
    );
}

#[test]
fn native_termvectors_generate_keyword_raw_and_text_vectors_without_term_vector_mapping() {
    let engine = TantivyEngine::default();
    engine
        .create_index(CreateIndexRequest {
            index: "termvectors".into(),
            settings: json!({}),
            mappings: json!({"properties": {
                "tag": {"type": "keyword"},
                "body": {"type": "text", "index_options": "docs"}
            }}),
        })
        .unwrap();
    engine
        .index_document(IndexDocumentRequest {
            index: "termvectors".into(),
            id: "generated".into(),
            source: json!({
                "tag": ["Café 😀", "Café 😀"],
                "body": "alpha alpha beta"
            }),
        })
        .unwrap();

    let options = NativeTermVectorOptions {
        fields: Some(["tag".to_owned(), "body".to_owned()].into_iter().collect()),
        per_field_analyzer: BTreeMap::new(),
        positions: true,
        offsets: true,
        field_statistics: false,
        term_statistics: false,
    };
    let expected_fields = json!({
        "tag": {
            "terms": {
                "Café 😀": {
                    "term_freq": 2,
                    "tokens": [
                        {"position": 0, "start_offset": 0, "end_offset": 7},
                        {"position": 1, "start_offset": 8, "end_offset": 15}
                    ]
                }
            }
        },
        "body": {
            "terms": {
                "alpha": {
                    "term_freq": 2,
                    "tokens": [
                        {"position": 0, "start_offset": 0, "end_offset": 5},
                        {"position": 1, "start_offset": 6, "end_offset": 11}
                    ]
                },
                "beta": {
                    "term_freq": 1,
                    "tokens": [{"position": 2, "start_offset": 12, "end_offset": 16}]
                }
            }
        }
    });

    let realtime = engine
        .get_native_termvectors(
            GetDocumentRequest {
                index: "termvectors".into(),
                id: "generated".into(),
            },
            None,
            &options,
            true,
        )
        .unwrap()
        .unwrap();
    assert_eq!(
        serde_json::to_value(&realtime.fields).unwrap(),
        expected_fields
    );
    let default_realtime = engine
        .get_native_termvectors(
            GetDocumentRequest {
                index: "termvectors".into(),
                id: "generated".into(),
            },
            None,
            &NativeTermVectorOptions::default(),
            true,
        )
        .unwrap()
        .unwrap();
    assert!(default_realtime.fields.is_empty());

    engine
        .refresh(RefreshRequest {
            indices: vec!["termvectors".into()],
        })
        .unwrap();
    let refreshed = engine
        .get_native_refreshed_termvectors(
            GetDocumentRequest {
                index: "termvectors".into(),
                id: "generated".into(),
            },
            None,
            &options,
        )
        .unwrap()
        .unwrap();
    assert_eq!(
        serde_json::to_value(&refreshed.fields).unwrap(),
        expected_fields
    );
    let default_refreshed = engine
        .get_native_refreshed_termvectors(
            GetDocumentRequest {
                index: "termvectors".into(),
                id: "generated".into(),
            },
            None,
            &NativeTermVectorOptions::default(),
        )
        .unwrap()
        .unwrap();
    assert!(default_refreshed.fields.is_empty());
}
