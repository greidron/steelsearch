use super::*;

#[test]
fn native_integer_range_candidates_match_source_for_exact_values() {
    for (shards, fast) in [(1, true), (3, true), (1, false), (3, false)] {
        let engine = TantivyEngine::default();
        engine.create_index(CreateIndexRequest {
            index: "exact-range".into(),
            settings: serde_json::json!({"number_of_shards": shards}),
            mappings: serde_json::json!({"properties": {"n": {"type": "long", "doc_values": fast}}}),
        }).unwrap();
        let values = [
            Value::Null,
            serde_json::json!([]),
            serde_json::json!([null]),
            serde_json::json!([[-2, null], [0, 2]]),
            serde_json::json!(i64::MIN),
            serde_json::json!(i64::MIN + 1),
            serde_json::json!(-2),
            serde_json::json!(0),
            serde_json::json!(2),
            serde_json::json!(9_007_199_254_740_992_i64),
            serde_json::json!(9_007_199_254_740_993_i64),
            serde_json::json!(i64::MAX - 1),
            serde_json::json!(i64::MAX),
        ];
        for (id, value) in values.into_iter().enumerate() {
            engine
                .index_document(IndexDocumentRequest {
                    index: "exact-range".into(),
                    id: id.to_string(),
                    source: serde_json::json!({"n": value}),
                })
                .unwrap();
        }
        engine
            .index_document(IndexDocumentRequest {
                index: "exact-range".into(),
                id: "missing".into(),
                source: serde_json::json!({}),
            })
            .unwrap();
        engine
            .refresh(RefreshRequest {
                indices: vec!["exact-range".into()],
            })
            .unwrap();
        let store = engine.store.read().unwrap();
        let index = &store.indices["exact-range"];
        let endpoints = [
            i64::MIN,
            i64::MIN + 1,
            -2,
            0,
            2,
            9_007_199_254_740_992,
            9_007_199_254_740_993,
            i64::MAX - 1,
            i64::MAX,
        ];
        let mut cases = Vec::new();
        for endpoint in endpoints {
            for operator in ["gt", "gte", "lt", "lte"] {
                cases.push(serde_json::json!({operator: endpoint}));
            }
        }
        for (offset, lower) in endpoints.iter().enumerate() {
            for upper in &endpoints[offset..] {
                for lower_operator in ["gt", "gte"] {
                    for upper_operator in ["lt", "lte"] {
                        cases.push(
                            serde_json::json!({lower_operator: lower, upper_operator: upper}),
                        );
                    }
                }
            }
        }
        assert_eq!(cases.len(), 216);
        for bounds in cases {
            let query = parse_query(&serde_json::json!({"range": {"n": bounds}})).unwrap();
            let native = index
                .search_documents_for_tantivy_query_unordered(&query)
                .unwrap()
                .unwrap()
                .into_iter()
                .map(|document| document.metadata.id.clone())
                .collect::<BTreeSet<_>>();
            let source = index
                .refreshed_documents_for_shards(None)
                .into_iter()
                .filter(|document| {
                    index
                        .score_document_query(&query, document)
                        .unwrap()
                        .is_some()
                })
                .map(|document| document.metadata.id.clone())
                .collect::<BTreeSet<_>>();
            assert_eq!(
                native, source,
                "shards={shards} fast={fast} bounds={bounds}"
            );
        }
    }
}

#[test]
fn native_integer_range_candidates_still_need_source_guard() {
    // These are internal-path counterexamples, not assertions of OpenSearch compatibility.
    let cases = [
        (
            "unsigned-source",
            serde_json::json!({"n": u64::MAX}),
            "n",
            serde_json::json!({"lt": 0}),
            true,
            false,
        ),
        (
            "unsigned-bound",
            serde_json::json!({"n": -1}),
            "n",
            serde_json::json!({"gte": u64::MAX}),
            true,
            false,
        ),
        (
            "dual-lower",
            serde_json::json!({"n": 0}),
            "n",
            serde_json::json!({"gte": 0, "gt": 1}),
            true,
            false,
        ),
        (
            "dual-upper",
            serde_json::json!({"n": 0}),
            "n",
            serde_json::json!({"lte": 0, "lt": -1}),
            true,
            false,
        ),
        (
            "object-array",
            serde_json::json!({"obj": [{"n": 0}]}),
            "obj.n",
            serde_json::json!({"gte": 0}),
            true,
            false,
        ),
        (
            "float-source",
            serde_json::json!({"n": 0.5}),
            "n",
            serde_json::json!({"gte": 0, "lte": 1}),
            false,
            true,
        ),
        (
            "unbounded-null",
            serde_json::json!({"n": null}),
            "n",
            serde_json::json!({}),
            false,
            true,
        ),
    ];
    for shards in [1, 3] {
        for (name, source, field, bounds, native_expected, source_expected) in &cases {
            let engine = TantivyEngine::default();
            engine
                .create_index(CreateIndexRequest {
                    index: "range-guard".into(),
                    settings: serde_json::json!({"number_of_shards": shards}),
                    mappings: serde_json::json!({"properties": {
                        "n": {"type": "long"},
                        "obj": {"properties": {"n": {"type": "long"}}}
                    }}),
                })
                .unwrap();
            engine
                .index_document(IndexDocumentRequest {
                    index: "range-guard".into(),
                    id: "doc".into(),
                    source: source.clone(),
                })
                .unwrap();
            engine
                .refresh(RefreshRequest {
                    indices: vec!["range-guard".into()],
                })
                .unwrap();
            let store = engine.store.read().unwrap();
            let index = &store.indices["range-guard"];
            let query = parse_query(&serde_json::json!({"range": {(*field): bounds}})).unwrap();
            let native = index
                .search_documents_for_tantivy_query_unordered(&query)
                .unwrap()
                .unwrap();
            let document = index.refreshed_document_by_id("doc").unwrap();
            let matched = index
                .score_document_query(&query, document)
                .unwrap()
                .is_some();
            assert_eq!(
                !native.is_empty(),
                *native_expected,
                "shards={shards} case={name}"
            );
            assert_eq!(matched, *source_expected, "shards={shards} case={name}");
            if *native_expected && !source_expected {
                let query = Query::Bool {
                    clauses: BoolQuery {
                        must: vec![Query::MatchAll],
                        filter: vec![query],
                        ..Default::default()
                    },
                };
                let (total, hits) = index
                    .search_hits_page_for_source_candidate_post_filter(
                        "range-guard",
                        &query,
                        &[],
                        0,
                        10,
                        None,
                    )
                    .unwrap()
                    .unwrap();
                assert_eq!(total, 0, "source guard must reject {name}");
                assert!(hits.is_empty());
            }
        }
    }
}

#[test]
fn deferred_bool_must_preserves_scores_and_error_visibility() {
    for shards in [1, 3] {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "deferred-bool".into(),
                settings: serde_json::json!({"number_of_shards":shards}),
                mappings: serde_json::json!({"properties":{
                    "title":{"type":"text", "fields":{"raw":{"type":"keyword"}}},
                    "body":{"type":"text"}, "service":{"type":"keyword"}, "latency":{"type":"long"}
                }}),
            })
            .unwrap();
        for id in 0..12 {
            engine.index_document(IndexDocumentRequest {
                index:"deferred-bool".into(), id:id.to_string(),
                source:serde_json::json!({
                    "title":if id % 3 == 0 {Value::Null} else {serde_json::json!("alpha beta")},
                    "body":if id % 2 == 0 {serde_json::json!(["alpha", "gap beta"])} else {serde_json::json!("other")},
                    "service":if id % 4 == 0 {"selected"} else {"other"}, "latency":id * 100
                }),
            }).unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["deferred-bool".into()],
            })
            .unwrap();
        let store = engine.store.read().unwrap();
        let index = &store.indices["deferred-bool"];
        for boost in [0.0, 0.5, 100_000_000.0] {
            for minimum in 0..=3 {
                for limit in [200, 2000] {
                    for excluded in ["selected", "absent"] {
                        for nested_bool in [false, true] {
                            let mut must = serde_json::json!({"multi_match":{
                                "query":"alpha", "fields":["title^2", "body^0.5"],
                                "type":"best_fields", "tie_breaker":0.3, "boost":boost
                            }});
                            if nested_bool {
                                must = serde_json::json!({"bool":{"must":must,"filter":{"match_all":{}}}});
                            }
                            let query = parse_query(&serde_json::json!({"bool":{
                                "must":must,
                                "filter":{"range":{"latency":{"lte":limit}}},
                                "must_not":{"term":{"service":excluded}},
                                "should":[{"match_phrase":{"body":{"query":"alpha beta","slop":1}}},
                                    {"term":{"service":"selected"}}],
                                "minimum_should_match":minimum
                            }}))
                            .unwrap();
                            let mut context = Bm25Context::default();
                            index
                                .prepare_source_bm25_matches(&query, None, &mut context)
                                .unwrap();
                            assert_eq!(
                                context.deferred_bool_must.len(),
                                if nested_bool { 2 } else { 1 }
                            );
                            for document in index.refreshed_documents_for_shards(None) {
                                let expected =
                                    index.score_document_query(&query, document).unwrap();
                                let actual = index
                                    .score_document_query_with_bm25_context(
                                        &query,
                                        document,
                                        &mut context,
                                    )
                                    .unwrap();
                                assert_eq!(
                                    actual.map(f32::to_bits),
                                    expected.map(f32::to_bits),
                                    "shards={shards} {query:?} id={}",
                                    document.metadata.id
                                );
                            }
                        }
                    }
                }
            }
        }
        let invalid = Query::Term {
            field: "title.raw".into(),
            value: serde_json::json!({"invalid":true}),
            case_insensitive: false,
        };
        for clauses in [
            BoolQuery {
                must: vec![invalid.clone()],
                filter: vec![Query::MatchNone],
                ..Default::default()
            },
            BoolQuery {
                must: vec![Query::MatchNone],
                filter: vec![invalid.clone()],
                ..Default::default()
            },
            BoolQuery {
                must: vec![Query::MatchNone],
                should: vec![invalid],
                minimum_should_match: Some(1),
                ..Default::default()
            },
        ] {
            let query = Query::Bool { clauses };
            let mut context = Bm25Context::default();
            index
                .prepare_source_bm25_matches(&query, None, &mut context)
                .unwrap();
            assert!(context.deferred_bool_must.is_empty());
            let document = index.refreshed_document_by_id("1").unwrap();
            let expected = index.score_document_query(&query, document);
            let actual =
                index.score_document_query_with_bm25_context(&query, document, &mut context);
            assert_eq!(format!("{actual:?}"), format!("{expected:?}"));
            if let Query::Bool { clauses } = &query {
                assert_eq!(
                    actual.is_err(),
                    !matches!(clauses.must[0], Query::MatchNone)
                );
            }
        }
        let text_range = parse_query(&serde_json::json!({"range":{"title":{"gte":"a"}}})).unwrap();
        assert!(!index.source_score_query_is_infallible(&text_range));
        let query = parse_query(&serde_json::json!({"bool":{
            "must":{"match":{"title":"unneeded"}}, "filter":{"match_none":{}}
        }}))
        .unwrap();
        let mut context = Bm25Context::default();
        index
            .prepare_source_bm25_matches(&query, None, &mut context)
            .unwrap();
        assert_eq!(context.deferred_bool_must.len(), 1);
        context.query_tokens.clear();
        context.native_matches.clear();
        assert!(index
            .score_document_query_with_bm25_context(
                &query,
                index.refreshed_document_by_id("1").unwrap(),
                &mut context,
            )
            .unwrap()
            .is_none());
        assert!(
            context.query_tokens.is_empty(),
            "rejected candidate must not score its must clause"
        );
    }
}

#[test]
fn compact_ranking_scores_preserve_heap_accumulation_bits() {
    let engine = TantivyEngine::default();
    engine
        .create_index(CreateIndexRequest {
            index: "compact-ranking".into(),
            settings: serde_json::json!({"number_of_shards":3}),
            mappings: serde_json::json!({"properties": {
                "title":{"type":"text"}, "body":{"type":"text"}
            }}),
        })
        .unwrap();
    for id in 0..9 {
        engine
            .index_document(IndexDocumentRequest {
                index: "compact-ranking".into(),
                id: id.to_string(),
                source: serde_json::json!({
                    "title":if id == 0 {Value::Null} else {
                        serde_json::json!(format!("alpha beta {}", "alpha ".repeat(id)))
                    },
                    "body":if id % 2 == 0 {"alpha gap beta"} else {"other"}
                }),
            })
            .unwrap();
    }
    engine
        .refresh(RefreshRequest {
            indices: vec!["compact-ranking".into()],
        })
        .unwrap();
    let store = engine.store.read().unwrap();
    let index = &store.indices["compact-ranking"];
    let field_sets = [
        vec![],
        vec!["title"],
        vec!["title^2", "body^0.5"],
        vec!["title^0", "missing"],
        vec!["body", "title", "title^2"],
        vec!["title^0", "body^0.5", "title^8", "missing"],
    ];
    for fields in field_sets {
        let fields = fields.into_iter().map(str::to_string).collect::<Vec<_>>();
        for kind in [
            MultiMatchType::BestFields,
            MultiMatchType::MostFields,
            MultiMatchType::Phrase,
            MultiMatchType::PhrasePrefix,
        ] {
            for tie in [0.0, 0.3, 1.0, 2.0] {
                for text in ["alpha", "alpha beta", "alpha be", "missing", ""] {
                    let query = serde_json::json!(text);
                    for document in index.refreshed_documents_for_shards(None) {
                        let mut scores = fields
                            .iter()
                            .filter_map(|field| {
                                let (field, boost) = multi_match_field_and_boost(field);
                                match kind {
                                    MultiMatchType::BestFields | MultiMatchType::MostFields => {
                                        index.opensearch_match_bm25_score(field, &query, document)
                                    }
                                    _ => index.opensearch_phrase_bm25_score(
                                        field,
                                        &query,
                                        1,
                                        matches!(kind, MultiMatchType::PhrasePrefix),
                                        document,
                                    ),
                                }
                                .map(|score| score * boost)
                            })
                            .collect::<Vec<_>>();
                        let expected = if scores.is_empty() {
                            None
                        } else if matches!(kind, MultiMatchType::MostFields) {
                            Some(scores.into_iter().sum::<f32>())
                        } else {
                            scores.sort_by(|a, b| {
                                b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal)
                            });
                            Some(scores[0] + scores.iter().skip(1).sum::<f32>() * tie)
                        };
                        let actual = index.opensearch_multi_match_bm25_score_with_bm25_context(
                            &fields,
                            &query,
                            kind,
                            1,
                            tie,
                            document,
                            &mut Bm25Context::default(),
                        );
                        assert_eq!(
                            actual.map(f32::to_bits),
                            expected.map(f32::to_bits),
                            "{fields:?} {kind:?} {tie} {text} {}",
                            document.metadata.id
                        );
                    }
                }
            }
        }
    }
    for must_boost in [0.0, 0.5, 100_000_000.0] {
        for should_count in 0..=8 {
            for minimum in 0..=should_count + 1 {
                let should = (0..should_count)
                    .map(|i| {
                        serde_json::json!({"match":{
                            "title":{"query":if i % 3 == 0 {"missing"} else {"alpha"},
                                "boost":(i + 1) as f64 * 0.5}
                        }})
                    })
                    .collect::<Vec<_>>();
                let query = parse_query(&serde_json::json!({"bool":{
                    "must":{"match":{"body":{"query":"alpha","boost":must_boost}}},
                    "should":should, "minimum_should_match":minimum
                }}))
                .unwrap();
                let Query::Bool { clauses } = &query else {
                    unreachable!()
                };
                for document in index.refreshed_documents_for_shards(None) {
                    let must = index
                        .score_document_query(&clauses.must[0], document)
                        .unwrap();
                    let should = clauses
                        .should
                        .iter()
                        .map(|q| index.score_document_query(q, document))
                        .collect::<EngineResult<Vec<_>>>()
                        .unwrap();
                    let expected = must.and_then(|must| {
                        if should.iter().flatten().count()
                            < effective_bool_minimum_should_match(clauses) as usize
                        {
                            return None;
                        }
                        let score = (0.0_f32 + must) + should.into_iter().flatten().sum::<f32>();
                        Some(if score == 0.0 { 1.0 } else { score })
                    });
                    let actual = index.score_document_query(&query, document).unwrap();
                    assert_eq!(
                        actual.map(f32::to_bits),
                        expected.map(f32::to_bits),
                        "{query:?}"
                    );
                }
            }
        }
    }
}

#[test]
fn source_bm25_query_tokens_are_shared_only_within_request() {
    let mut context = Bm25Context::default();
    for query in [
        serde_json::json!("Alpha beta beta"),
        serde_json::json!(42),
        serde_json::json!(true),
        serde_json::json!(""),
        serde_json::json!("  "),
    ] {
        let expected = tokenize_phrase_text(&json_value_to_query_text(&query).unwrap());
        let first = context.tokens(&query).unwrap();
        let second = context.tokens(&query).unwrap();
        assert_eq!(first.as_ref(), &expected);
        assert!(Arc::ptr_eq(&first, &second));
        let other_request = Bm25Context::default().tokens(&query).unwrap();
        assert!(!Arc::ptr_eq(&first, &other_request));
    }
    for invalid in [Value::Null, serde_json::json!([]), serde_json::json!({})] {
        assert!(context.tokens(&invalid).is_none());
    }
    assert_eq!(context.query_tokens.len(), 5);
    assert!(context.fields.is_empty());
}

#[test]
fn source_bm25_cached_queries_preserve_match_and_phrase_scores() {
    let engine = TantivyEngine::default();
    engine
        .create_index(CreateIndexRequest {
            index: "query-token-cache".into(),
            settings: serde_json::json!({"number_of_shards":3}),
            mappings: serde_json::json!({"properties":{"title":{"type":"text"}}}),
        })
        .unwrap();
    for (id, value) in [
        serde_json::json!("alpha beta beta"),
        serde_json::json!("beta alpha gamma"),
        serde_json::json!(["alpha", "beta"]),
        Value::Null,
    ]
    .into_iter()
    .enumerate()
    {
        engine
            .index_document(IndexDocumentRequest {
                index: "query-token-cache".into(),
                id: id.to_string(),
                source: serde_json::json!({"title":value}),
            })
            .unwrap();
    }
    engine
        .refresh(RefreshRequest {
            indices: vec!["query-token-cache".into()],
        })
        .unwrap();
    let store = engine.store.read().unwrap();
    let index = &store.indices["query-token-cache"];
    let mut context = Bm25Context::default();
    for query in ["alpha beta", "beta beta", "alpha be", "", "missing"] {
        let query = serde_json::json!(query);
        for id in 0..4 {
            let document = index.refreshed_document_by_id(&id.to_string()).unwrap();
            assert_eq!(
                index.opensearch_match_bm25_score("title", &query, document),
                index.opensearch_match_bm25_score_with_bm25_context(
                    "title",
                    &query,
                    document,
                    &mut context
                )
            );
            for slop in [0, 1, 3] {
                for prefix in [false, true] {
                    assert_eq!(
                        index.opensearch_phrase_bm25_score("title", &query, slop, prefix, document),
                        index.opensearch_phrase_bm25_score_with_bm25_context(
                            "title",
                            &query,
                            slop,
                            prefix,
                            1.0,
                            document,
                            &mut context
                        )
                    );
                }
            }
        }
    }
    assert_eq!(context.query_tokens.len(), 5);
}

#[test]
fn postings_bm25_preserves_source_bits_and_unsafe_fields_fall_back() {
    for shards in [1, 3] {
        for field_override in [
            None,
            Some("x".repeat(39)),
            Some("x".repeat(40)),
            Some("\u{00e9}".into()),
        ] {
            let engine = TantivyEngine::default();
            engine.create_index(CreateIndexRequest {
                index: "postings-bm25".into(), settings: serde_json::json!({"number_of_shards":shards}),
                mappings: serde_json::json!({"properties":{
                    "title":{"type":"text"}, "message":{"type":"text"}, "keep":{"type":"boolean"}
                }}),
            }).unwrap();
            for id in 0..40 {
                let mut source = serde_json::json!({
                    "title":[format!("alpha {}", "beta ".repeat(id % 7)), "OTHER"],
                    "message":format!("alpha gamma {}", "other ".repeat(id * 3)),
                    "keep":id % 2 == 0,
                });
                if let Some(text) = &field_override {
                    source["title"] = serde_json::json!(text);
                }
                engine
                    .index_document(IndexDocumentRequest {
                        index: "postings-bm25".into(),
                        id: id.to_string(),
                        source,
                    })
                    .unwrap();
            }
            engine
                .refresh(RefreshRequest {
                    indices: vec!["postings-bm25".into()],
                })
                .unwrap();
            let store = engine.store.read().unwrap();
            let index = &store.indices["postings-bm25"];
            for text in [
                "alpha beta alpha".to_string(),
                "missing".into(),
                "ALPHA gamma".into(),
                "alpha OR beta".into(),
                "x".repeat(39),
            ] {
                for mode in ["best_fields", "most_fields"] {
                    let query = parse_query(&serde_json::json!({"bool":{
                        "must":{"multi_match":{"query":text,"fields":["title^2","message"],"type":mode,"boost":0.5}},
                        "should":[{"match_phrase":{"message":{"query":"alpha gamma","slop":1}}},
                            {"term":{"keep":true}}],"minimum_should_match":1
                    }})).unwrap();
                    let mut context = Bm25Context::default();
                    index
                        .prepare_source_bm25_matches(&query, None, &mut context)
                        .unwrap();
                    let safe_title = field_override
                        .as_ref()
                        .map_or(true, |text| text.is_ascii() && text.len() < 40);
                    assert_eq!(context.native_matches.len(), if safe_title { 2 } else { 1 });
                    for document in index.refreshed_documents_for_shards(None) {
                        let expected = index
                            .score_document_query(&query, document)
                            .unwrap()
                            .map(f32::to_bits);
                        let actual = index
                            .score_document_query_with_bm25_context(&query, document, &mut context)
                            .unwrap()
                            .map(f32::to_bits);
                        assert_eq!(
                            actual, expected,
                            "shards={shards} mode={mode} text={text} id={}",
                            document.metadata.id
                        );
                    }
                }
            }
        }
    }
}

#[test]
fn postings_bm25_cache_budget_falls_back_without_losing_matches() {
    let engine = TantivyEngine::default();
    engine
        .create_index(CreateIndexRequest {
            index: "postings-budget".into(),
            settings: serde_json::json!({"number_of_shards":1}),
            mappings: serde_json::json!({"properties":{"title":{"type":"text"}}}),
        })
        .unwrap();
    engine
        .index_document(IndexDocumentRequest {
            index: "postings-budget".into(),
            id: "1".into(),
            source: serde_json::json!({"title":"alpha beta"}),
        })
        .unwrap();
    engine
        .refresh(RefreshRequest {
            indices: vec!["postings-budget".into()],
        })
        .unwrap();
    let store = engine.store.read().unwrap();
    let index = &store.indices["postings-budget"];
    let query = parse_query(&serde_json::json!({"match":{"title":"alpha"}})).unwrap();
    let mut context = Bm25Context::default();
    context.native_matches.push(PreparedSourceBm25Match {
        field: "other".into(),
        query: serde_json::json!("other"),
        scores: BTreeMap::from([(
            0,
            (0..MAX_PREPARED_SOURCE_BM25_SCORES)
                .map(|id| (id.to_string(), 1.0))
                .collect(),
        )]),
    });
    index
        .prepare_source_bm25_matches(&query, None, &mut context)
        .unwrap();
    assert_eq!(context.native_matches.len(), 1);
    let document = index.refreshed_document_by_id("1").unwrap();
    assert_eq!(
        index
            .score_document_query_with_bm25_context(&query, document, &mut context)
            .unwrap(),
        index.score_document_query(&query, document).unwrap()
    );
    assert!(index
        .score_document_query(&query, document)
        .unwrap()
        .is_some());
}

#[test]
fn prepared_source_phrases_preserve_scores_and_fallback_contracts() {
    let engine = TantivyEngine::default();
    engine
        .create_index(CreateIndexRequest {
            index: "phrase-dispatch".into(),
            settings: serde_json::json!({"number_of_shards":3}),
            mappings: serde_json::json!({"properties":{
                "title":{"type":"text"}, "code":{"type":"keyword"}
            }}),
        })
        .unwrap();
    let titles = serde_json::json!([
        "alpha beta",
        "alpha gap beta",
        "alpha gamma",
        "beta alpha",
        "!!!",
        null,
        [],
        ["alpha", "beta"],
        "\u{00e9}clair beta"
    ]);
    for (id, title) in titles.as_array().unwrap().iter().enumerate() {
        engine
            .index_document(IndexDocumentRequest {
                index: "phrase-dispatch".into(),
                id: id.to_string(),
                source: serde_json::json!({"title":title,"code":"alpha beta"}),
            })
            .unwrap();
    }
    engine
        .refresh(RefreshRequest {
            indices: vec!["phrase-dispatch".into()],
        })
        .unwrap();
    let store = engine.store.read().unwrap();
    let index = &store.indices["phrase-dispatch"];
    for field in ["title", "code"] {
        for kind in ["match_phrase", "match_phrase_prefix"] {
            for text in serde_json::json!([
                "alpha beta",
                "alpha be",
                "missing",
                "",
                "!!!",
                "\u{00e9}clair",
                123,
                true
            ])
            .as_array()
            .unwrap()
            {
                for slop in [0, 1, 3] {
                    for analyzer in [None, Some("keyword")] {
                        for zero_all in [false, true] {
                            let mut spec = serde_json::json!({"query":text,"slop":slop,"boost":0.5,
                                "zero_terms_query":if zero_all {"all"} else {"none"}});
                            if let Some(analyzer) = analyzer {
                                spec["analyzer"] = serde_json::json!(analyzer);
                            }
                            let query =
                                parse_query(&serde_json::json!({(kind):{(field):spec}})).unwrap();
                            let mut context = Bm25Context::default();
                            index
                                .prepare_source_bm25_matches(&query, None, &mut context)
                                .unwrap();
                            let eligible = field == "title"
                                && analyzer.is_none()
                                && !zero_all
                                && text
                                    .as_str()
                                    .is_some_and(|text| text.chars().any(char::is_alphanumeric));
                            assert_eq!(
                                context.complete_source_phrases.len(),
                                usize::from(eligible)
                            );
                            for document in index.refreshed_documents_for_shards(None) {
                                let expected = index
                                    .score_document_query(&query, document)
                                    .unwrap()
                                    .map(f32::to_bits);
                                let actual = index
                                    .score_document_query_with_bm25_context(
                                        &query,
                                        document,
                                        &mut context,
                                    )
                                    .unwrap()
                                    .map(f32::to_bits);
                                assert_eq!(
                                    actual, expected,
                                    "{query:?} id={}",
                                    document.metadata.id
                                );
                            }
                        }
                    }
                }
            }
        }
    }
}

#[test]
fn source_shard_statistics_and_native_pages_match_live_reference() {
    let fixture: Value = serde_json::from_str(include_str!(
        "../../../tools/fixtures/search-bm25-shard-native-compat.json"
    ))
    .unwrap();
    let engine = TantivyEngine::default();
    let name = fixture["indices"][0]["name"].as_str().unwrap();
    let body = &fixture["indices"][0]["body"];
    engine
        .create_index(CreateIndexRequest {
            index: name.into(),
            settings: body["settings"].clone(),
            mappings: body["mappings"].clone(),
        })
        .unwrap();
    for document in fixture["bulk"][0]["documents"].as_array().unwrap() {
        engine
            .index_document(IndexDocumentRequest {
                index: name.into(),
                id: document["_id"].as_str().unwrap().into(),
                source: document["_source"].clone(),
            })
            .unwrap();
    }
    engine
        .refresh(RefreshRequest {
            indices: vec![name.into()],
        })
        .unwrap();
    let store = engine.store.read().unwrap();
    let index = &store.indices[name];
    let expected = [
        ("len-1", 0.140054_f32),
        ("len-40", 0.130765),
        ("len-42", 0.083669),
        ("len-44", 0.082092),
        ("len-1000", 0.059399),
    ];
    let mut context = Bm25Context::default();
    for case in fixture["cases"].as_array().unwrap() {
        let body = &case["steps"][0]["body"];
        let query = parse_query(&body["query"]).unwrap();
        let boost = if case["name"].as_str().unwrap().contains("multi-match") {
            2.0
        } else {
            1.0
        };
        for (id, score) in expected {
            let document = index.refreshed_document_by_id(id).unwrap();
            let actual = index
                .score_document_query_with_bm25_context(&query, document, &mut context)
                .unwrap()
                .unwrap();
            assert!((actual - score * boost).abs() < 2e-6, "{id}: {actual}");
        }
        let from = body["from"].as_u64().unwrap() as usize;
        let size = body["size"].as_u64().unwrap() as usize;
        let (total, hits) = index
            .search_hits_page_for_query_native_scoped(name, None, &query, &[], from, size)
            .unwrap()
            .unwrap();
        assert_eq!(total, 5);
        let page = expected.iter().skip(from).take(size).collect::<Vec<_>>();
        assert_eq!(hits.len(), page.len());
        for (hit, &&(id, score)) in hits.iter().zip(page.iter()) {
            assert_eq!(hit.metadata.id, id);
            assert!((hit.score - score * boost).abs() < 2e-6);
        }
    }
    assert_eq!(context.fields.len(), 3);
    assert_eq!(
        context
            .fields
            .values()
            .map(|fields| fields["title"].doc_count)
            .sum::<usize>(),
        5
    );
}

#[test]
fn native_bool_multi_match_scores_equal_source_before_page_selection() {
    let engine = TantivyEngine::default();
    engine
        .create_index(CreateIndexRequest {
            index: "native-bool-ranking".into(),
            settings: serde_json::json!({"number_of_shards":1}),
            mappings: serde_json::json!({"properties": {
                "title":{"type":"text"}, "body":{"type":"text"}, "service":{"type":"keyword"}
            }}),
        })
        .unwrap();
    for i in 0..40 {
        engine
            .index_document(IndexDocumentRequest {
                index: "native-bool-ranking".into(),
                id: format!("doc-{i:02}"),
                source: serde_json::json!({
                    "title":format!("{} {}", "alpha ".repeat(1 + i % 7), "other ".repeat(i * 3)),
                    "body":if i % 3 == 0 { Value::Null } else {
                        serde_json::json!(format!("alpha {}", "other ".repeat(i * 5)))
                    },
                    "service":if i % 2 == 0 {"featured"} else {"ordinary"}
                }),
            })
            .unwrap();
    }
    engine
        .refresh(RefreshRequest {
            indices: vec!["native-bool-ranking".into()],
        })
        .unwrap();
    let store = engine.store.read().unwrap();
    let index = &store.indices["native-bool-ranking"];
    let state = index.search_state.as_ref().unwrap();
    for kind in ["best_fields", "most_fields"] {
        for boost in [0.0, 0.5, 2.0] {
            let query = parse_query(&serde_json::json!({"bool": {
                "must":[{"multi_match":{"query":"alpha", "fields":["title^8", "body^2"],
                    "type":kind, "tie_breaker":0.3}}, {"match":{"title":{"query":"alpha", "boost":boost}}}],
                "should":{"term":{"service":"featured"}},
                "filter":{"match":{"title":"alpha"}}
            }})).unwrap();
            let built = build_tantivy_query(state, &query).unwrap().unwrap();
            let actual = state
                .searcher
                .search(built.as_ref(), &TopDocs::with_limit(40))
                .unwrap();
            assert_eq!(actual.len(), 40);
            for (score, address) in actual {
                let id = state
                    .document_id_for_address(&state.searcher, address)
                    .unwrap();
                let document = index.refreshed_document_by_id(id).unwrap();
                let expected = index
                    .score_document_query(&query, document)
                    .unwrap()
                    .unwrap();
                assert!(
                    (score - expected).abs() < 1e-5,
                    "kind={kind} boost={boost} id={id}: native={score} source={expected}"
                );
            }
        }
    }
}

#[test]
fn shared_length_norm_matches_native_encoding_boundaries() {
    use tantivy::fieldnorm::FieldNormReader;
    let boundaries = (0..=255).flat_map(|id| {
        let length = FieldNormReader::id_to_fieldnorm(id);
        [length.saturating_sub(1), length, length.saturating_add(1)]
    });
    for length in (0..=65536).chain(boundaries).chain([u32::MAX]) {
        let expected = FieldNormReader::id_to_fieldnorm(FieldNormReader::fieldnorm_to_id(length));
        assert_eq!(
            os_core::bm25::normalized_document_length(length as usize),
            expected as usize,
            "length={length}"
        );
    }
}

#[test]
fn native_bm25_scaling_requires_field_statistics_and_non_scoring_filters() {
    struct FieldStatistics<'a> {
        searcher: &'a tantivy::Searcher,
        documents: u64,
    }
    impl tantivy::query::Bm25StatisticsProvider for FieldStatistics<'_> {
        fn total_num_tokens(&self, field: tantivy::schema::Field) -> tantivy::Result<u64> {
            tantivy::query::Bm25StatisticsProvider::total_num_tokens(self.searcher, field)
        }
        fn total_num_docs(&self) -> tantivy::Result<u64> {
            Ok(self.documents)
        }
        fn doc_freq(&self, term: &tantivy::Term) -> tantivy::Result<u64> {
            self.searcher.doc_freq(term)
        }
    }
    for length in [5, 41, 1000] {
        for sparse in [false, true] {
            let engine = TantivyEngine::default();
            engine
                .create_index(CreateIndexRequest {
                    index: "native-score-boundary".into(),
                    settings: serde_json::json!({"number_of_shards":1}),
                    mappings: serde_json::json!({"properties": {
                        "title":{"type":"text"}, "service":{"type":"keyword"}
                    }}),
                })
                .unwrap();
            for (id, title) in [
                ("a", serde_json::json!("alpha")),
                (
                    "b",
                    serde_json::json!(format!("alpha {}", "other ".repeat(length - 1))),
                ),
                (
                    "c",
                    if sparse {
                        Value::Null
                    } else {
                        serde_json::json!("other")
                    },
                ),
            ] {
                engine
                    .index_document(IndexDocumentRequest {
                        index: "native-score-boundary".into(),
                        id: id.into(),
                        source: serde_json::json!({"title":title,"service":"yes"}),
                    })
                    .unwrap();
            }
            engine
                .refresh(RefreshRequest {
                    indices: vec!["native-score-boundary".into()],
                })
                .unwrap();
            let store = engine.store.read().unwrap();
            let index = &store.indices["native-score-boundary"];
            let state = index.search_state.as_ref().unwrap();
            let query = parse_query(&serde_json::json!({"match":{"title":"alpha"}})).unwrap();
            let native_scores = |query: &Query| {
                let built = build_tantivy_query(state, query).unwrap().unwrap();
                state
                    .searcher
                    .search(built.as_ref(), &TopDocs::with_limit(10))
                    .unwrap()
                    .into_iter()
                    .map(|(score, address)| {
                        (
                            state
                                .document_id_for_address(&state.searcher, address)
                                .unwrap()
                                .to_owned(),
                            score,
                        )
                    })
                    .collect::<BTreeMap<_, _>>()
            };
            let raw_query = QueryParser::for_index(
                &state.index,
                vec![state.searcher.schema().get_field("title").unwrap()],
            )
            .parse_query("alpha")
            .unwrap();
            let native = state
                .searcher
                .search(raw_query.as_ref(), &TopDocs::with_limit(10))
                .unwrap()
                .into_iter()
                .map(|(score, address)| {
                    (
                        state
                            .document_id_for_address(&state.searcher, address)
                            .unwrap()
                            .to_owned(),
                        score,
                    )
                })
                .collect::<BTreeMap<_, _>>();
            let normalized = native_scores(&query);
            let mut ratios = Vec::new();
            for id in ["a", "b"] {
                let document = index.refreshed_document_by_id(id).unwrap();
                let source = index
                    .score_document_query(&query, document)
                    .unwrap()
                    .unwrap();
                assert!(
                    (normalized[id] - source).abs() < 1e-6,
                    "production native score length={length} sparse={sparse} id={id}"
                );
                println!(
                    "sparse={sparse} id={id} native={} source={source}",
                    native[id]
                );
                ratios.push(native[id] / source);
                if !sparse {
                    assert!((native[id] / 2.2 - source).abs() < 1e-6);
                }
            }
            if sparse {
                assert!(
                    (ratios[0] - ratios[1]).abs() > 0.01,
                    "sparse fields cannot be corrected by one multiplier: {ratios:?}"
                );
            }
            let field = state.searcher.schema().get_field("title").unwrap();
            // This fixture has no deletes; deleted-document statistics need a separate contract.
            let documents = state
                .searcher
                .segment_readers()
                .iter()
                .map(|segment| {
                    let norms = segment.get_fieldnorms_reader(field).unwrap();
                    (0..segment.max_doc())
                        .filter(|&doc| norms.fieldnorm(doc) != 0)
                        .count() as u64
                })
                .sum::<u64>();
            assert_eq!(documents, if sparse { 2 } else { 3 });
            let statistics = FieldStatistics {
                searcher: &state.searcher,
                documents,
            };
            let built = raw_query;
            let weight = built
                .weight(
                    tantivy::query::EnableScoring::enabled_from_statistics_provider(
                        &statistics,
                        &state.searcher,
                    ),
                )
                .unwrap();
            for (_, address) in state
                .searcher
                .search(built.as_ref(), &TopDocs::with_limit(10))
                .unwrap()
            {
                let id = state
                    .document_id_for_address(&state.searcher, address)
                    .unwrap();
                let document = index.refreshed_document_by_id(id).unwrap();
                let expected = index
                    .score_document_query(&query, document)
                    .unwrap()
                    .unwrap();
                let mut scorer = weight
                    .scorer(
                        state.searcher.segment_reader(address.segment_ord),
                        1.0 / 2.2,
                    )
                    .unwrap();
                assert_eq!(scorer.seek(address.doc_id), address.doc_id);
                let corrected = scorer.score();
                assert!(
                    (corrected - expected).abs() < 1e-6,
                    "field-specific statistics sparse={sparse} id={id}: {corrected} != {expected}"
                );
                println!(
                    "field-statistics sparse={sparse} id={id} native={corrected} source={expected}"
                );
            }
            let filtered = parse_query(&serde_json::json!({"bool": {
                "must":{"match":{"title":"alpha"}}, "filter":{"term":{"service":"yes"}}
            }}))
            .unwrap();
            let filtered_native = native_scores(&filtered);
            for id in ["a", "b"] {
                assert_eq!(
                    filtered_native[id], normalized[id],
                    "filters must not add a native score"
                );
                let document = index.refreshed_document_by_id(id).unwrap();
                assert_eq!(
                    index.score_document_query(&filtered, document).unwrap(),
                    index.score_document_query(&query, document).unwrap()
                );
            }
            for minimum in [0, 1, 2] {
                let mut body = serde_json::json!({"bool": {
                    "must":{"match":{"title":"alpha"}},
                    "should":[{"term":{"service":"yes"}},{"term":{"service":"yes"}}],
                    "minimum_should_match": minimum
                }});
                let unfiltered = native_scores(&parse_query(&body).unwrap());
                body["bool"]["filter"] = serde_json::json!({"term":{"service":"yes"}});
                assert_eq!(
                    native_scores(&parse_query(&body).unwrap()),
                    unfiltered,
                    "minimum_should_match={minimum} must preserve non-scoring filters"
                );
                body["bool"]["filter"] = serde_json::json!({"term":{"service":"absent"}});
                assert!(native_scores(&parse_query(&body).unwrap()).is_empty());
            }
            let filter_only = parse_query(&serde_json::json!({"bool":{
                "filter":{"match":{"title":"alpha"}}
            }}))
            .unwrap();
            let filter_scores = native_scores(&filter_only);
            assert_eq!(filter_scores.len(), 2);
            assert!(filter_scores.values().all(|score| *score == 0.0));
        }
    }
}

#[test]
fn bool_multi_match_pages_preserve_native_scores_before_truncation() {
    for shards in [1, 3] {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "bool-score-pages".into(),
                settings: serde_json::json!({"number_of_shards": shards}),
                mappings: serde_json::json!({"properties": {
                    "title": {"type": "text"}, "service": {"type": "keyword"}
                }}),
            })
            .unwrap();
        for i in 0..40 {
            engine.index_document(IndexDocumentRequest {
                index: "bool-score-pages".into(), id: format!("doc-{i:02}"),
                source: serde_json::json!({
                    "title": format!("{} {}", "alpha ".repeat(1 + i % 7), "other ".repeat(i % 13)),
                    "service": if i % 3 == 0 { "featured" } else { "ordinary" }
                }),
            }).unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["bool-score-pages".into()],
            })
            .unwrap();
        let store = engine.store.read().unwrap();
        let index = &store.indices["bool-score-pages"];
        for mode in 0..3 {
            let mut body = serde_json::json!({"bool": {
                "must": [{"multi_match": {"query": "alpha", "fields": ["title^8"]}}],
                "should": [{"term": {"service": "featured"}}]
            }});
            if mode == 1 {
                body = serde_json::json!({"bool": {"must": [body]}});
            }
            if mode == 2 {
                body = serde_json::json!({"bool": {"should": [body]}});
            }
            let query = parse_query(&body).unwrap();
            assert!(query_requires_native_candidate_post_filter(&query));
            assert!(query_allows_source_candidate_scan_for_native_post_filter(
                &query
            ));
            assert!(index.native_compound_score_is_authoritative(&query, None));
            let native_scores =
                super::native_ranking_audit_tests::native_scores(index, &query, false);
            for selected in [
                None,
                Some(BTreeSet::new()),
                Some(BTreeSet::from([0])),
                Some((0..shards).collect::<BTreeSet<u32>>()),
            ] {
                for sort in [
                    Vec::<SortSpec>::new(),
                    vec![serde_json::from_value(
                        serde_json::json!({"field":"service", "order":"desc"}),
                    )
                    .unwrap()],
                ] {
                    let mut expected = index
                        .refreshed_documents_for_shards(selected.as_ref())
                        .into_iter()
                        .filter_map(|document| {
                            native_scores.get(&document.metadata.id).map(|&score| {
                                index.search_hit_for_document_with_score(
                                    "bool-score-pages",
                                    document,
                                    score,
                                    false,
                                )
                            })
                        })
                        .collect::<Vec<_>>();
                    if sort.is_empty() {
                        expected.sort_by(compare_relevance_hits);
                    } else if let Some(mapped_sort) =
                        MappedEngineSort::for_index("bool-score-pages", index, &sort).unwrap()
                    {
                        expected = mapped_sort.order_hits(expected).unwrap();
                    } else {
                        sort_hits(&mut expected, &sort);
                    }
                    for (from, size) in [(0, 1), (1, 3), (7, 10), (40, 5), (0, 0), (usize::MAX, 2)]
                    {
                        let (total, hits) = index.search_hits_page_for_query_native_scoped(
                            "bool-score-pages", selected.as_ref(), &query, &sort, from, size,
                        ).unwrap().unwrap_or_else(|| panic!(
                            "missing page: shards={shards}, mode={mode}, selected={selected:?}, sort={sort:?}, from={from}, size={size}"
                        ));
                        assert_eq!(total, expected.len() as u64);
                        let actual = hits
                            .into_iter()
                            .map(|hit| (hit.metadata.id, hit.score, hit.source))
                            .collect::<Vec<_>>();
                        let page = expected
                            .iter()
                            .skip(from)
                            .take(size)
                            .map(|hit| (hit.metadata.id.clone(), hit.score, hit.source.clone()))
                            .collect::<Vec<_>>();
                        assert_eq!(actual, page,
                            "shards={shards}, mode={mode}, selected={selected:?}, sort={sort:?}, from={from}, size={size}");
                    }
                }
            }
        }
    }
}

#[test]
fn field_annotations_preserve_existing_base_name_rules() {
    for (input, field, boost) in [
        ("title", "title", 1.0),
        ("title^2", "title", 2.0),
        ("object.title^0.5", "object.title", 0.5),
        ("_id^0", "_id", 0.0),
        ("a^b^3", "a^b", 3.0),
        ("^2", "^2", 1.0),
        ("title^NaN", "title^NaN", 1.0),
        ("title^inf", "title^inf", 1.0),
        ("title^bad", "title^bad", 1.0),
    ] {
        assert_eq!(multi_match_field_and_boost(input), (field, boost));
        assert_eq!(multi_match_base_field_name(input), field);
    }
}

#[test]
fn boosted_source_fields_match_base_fields_for_scalar_array_missing_and_id() {
    for source in [
        serde_json::json!({"title": "alpha", "object": {"title": "alpha"}}),
        serde_json::json!({"title": [null, "alpha", "other"]}),
        serde_json::json!({"title": null}),
        serde_json::json!({}),
    ] {
        for field in ["title", "object.title", "_id"] {
            for kind in [
                "best_fields",
                "most_fields",
                "phrase",
                "phrase_prefix",
                "bool_prefix",
            ] {
                let plain = parse_query(&serde_json::json!({"multi_match": {
                    "fields": [field], "query": "alpha", "type": kind
                }}))
                .unwrap();
                let boosted = parse_query(&serde_json::json!({"multi_match": {
                    "fields": [format!("{field}^2")], "query": "alpha", "type": kind
                }}))
                .unwrap();
                assert_eq!(
                    document_matches_query(&boosted, "alpha", &source),
                    document_matches_query(&plain, "alpha", &source),
                    "{kind}/{field}/{source}"
                );
                assert_eq!(
                    multi_match_matched_value_count(
                        "alpha",
                        &source,
                        &[format!("{field}^2")],
                        &Value::String("alpha".into())
                    ),
                    multi_match_matched_value_count(
                        "alpha",
                        &source,
                        &[field.into()],
                        &Value::String("alpha".into())
                    )
                );
            }
        }
    }
}

#[test]
fn native_and_source_multi_match_apply_per_field_boost() {
    let engine = TantivyEngine::default();
    engine
        .create_index(CreateIndexRequest {
            index: "field-boost".into(),
            settings: serde_json::json!({"number_of_shards": 1}),
            mappings: serde_json::json!({"properties": {"title": {"type": "text"}}}),
        })
        .unwrap();
    engine
        .index_document(IndexDocumentRequest {
            index: "field-boost".into(),
            id: "doc".into(),
            source: serde_json::json!({"title": "alpha beta"}),
        })
        .unwrap();
    engine
        .refresh(RefreshRequest {
            indices: vec!["field-boost".into()],
        })
        .unwrap();
    let store = engine.store.read().unwrap();
    let index = &store.indices["field-boost"];
    let document = index.documents.values().next().unwrap();
    let state = index.search_state.as_ref().unwrap();
    for kind in ["best_fields", "most_fields", "phrase", "phrase_prefix"] {
        let query_for = |field: &str| {
            parse_query(&serde_json::json!({"multi_match": {
                "fields": [field], "query": "alpha", "type": kind
            }}))
            .unwrap()
        };
        let plain = query_for("title");
        let boosted = query_for("title^2");
        let source_plain = index.opensearch_text_bm25_score(&plain, document).unwrap();
        let source_boosted = index
            .opensearch_text_bm25_score(&boosted, document)
            .unwrap();
        assert!(
            (source_boosted - 2.0 * source_plain).abs() < 1e-6,
            "source {kind}"
        );
        assert_eq!(
            index.score_document_query(&boosted, document).unwrap(),
            Some(source_boosted),
            "post-filter {kind}"
        );
        let native_score = |query: &Query| {
            let query = build_tantivy_query(state, query).unwrap().unwrap();
            state
                .searcher
                .search(query.as_ref(), &TopDocs::with_limit(1))
                .unwrap()[0]
                .0
        };
        assert!(
            (native_score(&boosted) - 2.0 * native_score(&plain)).abs() < 1e-6,
            "native {kind}"
        );
    }
}
