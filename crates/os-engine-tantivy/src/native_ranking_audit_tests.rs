use super::*;

use super::native_phrase_positions as phrase_positions;

#[test]
fn native_authority_metadata_refresh_and_replacement_do_not_build_source_statistics() {
    for shards in [1, 3] {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "metadata".into(),
                settings: serde_json::json!({"number_of_shards":shards}),
                mappings: serde_json::json!({"properties":{"title":{"type":"text"}}}),
            })
            .unwrap();
        let query =
            parse_query(&serde_json::json!({"bool":{"must":[{"match":{"title":"alpha"}}]}}))
                .unwrap();
        for (value, expected) in [
            (serde_json::json!("alpha beta"), true),
            (serde_json::json!(42), false),
            (serde_json::json!("alpha restored"), true),
        ] {
            engine
                .index_document(IndexDocumentRequest {
                    index: "metadata".into(),
                    id: "one".into(),
                    source: serde_json::json!({"title":value}),
                })
                .unwrap();
            engine
                .refresh(RefreshRequest {
                    indices: vec!["metadata".into()],
                })
                .unwrap();
            let store = engine.store.read().unwrap();
            let index = &store.indices["metadata"];
            index.bm25_stats_cache.lock().unwrap().clear();
            assert_eq!(
                index.native_compound_score_is_authoritative(&query, None),
                expected
            );
            assert!(index.bm25_stats_cache.lock().unwrap().is_empty());
        }
        engine
            .index_document(IndexDocumentRequest {
                index: "metadata".into(),
                id: "bad".into(),
                source: serde_json::json!({"title":false}),
            })
            .unwrap();
        engine
            .refresh(RefreshRequest {
                indices: vec!["metadata".into()],
            })
            .unwrap();
        engine
            .delete_document(os_engine::DeleteDocumentRequest {
                index: "metadata".into(),
                id: "bad".into(),
            })
            .unwrap();
        {
            let store = engine.store.read().unwrap();
            assert!(!store.indices["metadata"].native_compound_score_is_authoritative(&query, None));
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["metadata".into()],
            })
            .unwrap();
        let store = engine.store.read().unwrap();
        let index = &store.indices["metadata"];
        index.bm25_stats_cache.lock().unwrap().clear();
        assert!(index.native_compound_score_is_authoritative(&query, None));
        assert!(index.bm25_stats_cache.lock().unwrap().is_empty());
    }
}

#[test]
fn native_compound_authority_rejects_unproven_leaves_and_respects_shard_stats() {
    let engine = TantivyEngine::default();
    engine.create_index(CreateIndexRequest {index:"authority-guard".into(),
        settings:serde_json::json!({"number_of_shards":3}),
        mappings:serde_json::json!({"properties":{"title":{"type":"text"},"service":{"type":"keyword"}}}),
    }).unwrap();
    engine
        .index_document(IndexDocumentRequest {
            index: "authority-guard".into(),
            id: "good".into(),
            source: serde_json::json!({"title":"alpha beta","service":"yes"}),
        })
        .unwrap();
    engine
        .refresh(RefreshRequest {
            indices: vec!["authority-guard".into()],
        })
        .unwrap();
    let wrap = |leaf: Value| parse_query(&serde_json::json!({"bool":{"must":[leaf]}})).unwrap();
    let query =
        wrap(serde_json::json!({"multi_match":{"fields":["title^2"],"query":"alpha beta"}}));
    let (good_shard, bad_shard, bad_id) = {
        let store = engine.store.read().unwrap();
        let index = &store.indices["authority-guard"];
        assert!(index.native_compound_score_is_authoritative(&query, None));
        for leaf in [
            serde_json::json!({"match":{"title":"alpha OR beta"}}),
            serde_json::json!({"match":{"title":"alpha*"}}),
            serde_json::json!({"match":{"title":{"query":"alpha","fuzziness":1}}}),
            serde_json::json!({"match":{"title":{"query":"alpha","boost":0}}}),
            serde_json::json!({"match":{"missing":"alpha"}}),
            serde_json::json!({"match_phrase":{"title":{"query":"alpha beta","analyzer":"keyword"}}}),
            serde_json::json!({"multi_match":{"fields":["title"],"query":"alpha","type":"cross_fields"}}),
            serde_json::json!({"multi_match":{"fields":["title"],"query":"alpha","type":"most_fields","tie_breaker":0}}),
            serde_json::json!({"multi_match":{"fields":["service"],"query":"yes"}}),
            serde_json::json!({"constant_score":{"filter":{"match_all":{}}}}),
        ] {
            assert!(
                !index.native_compound_score_is_authoritative(&wrap(leaf.clone()), None),
                "{leaf}"
            );
        }
        let good = index.documents.shard_id_for_write("good", None);
        let (bad_id, bad) = (0..100)
            .map(|n| format!("bad-{n}"))
            .map(|id| {
                let shard = index.documents.shard_id_for_write(&id, None);
                (id, shard)
            })
            .find(|(_, shard)| *shard != good)
            .unwrap();
        (good, bad, bad_id)
    };
    engine
        .index_document(IndexDocumentRequest {
            index: "authority-guard".into(),
            id: bad_id,
            source: serde_json::json!({"title":5,"service":"yes"}),
        })
        .unwrap();
    engine
        .refresh(RefreshRequest {
            indices: vec!["authority-guard".into()],
        })
        .unwrap();
    let store = engine.store.read().unwrap();
    let index = &store.indices["authority-guard"];
    assert!(!index.native_compound_score_is_authoritative(&query, None));
    assert!(
        index.native_compound_score_is_authoritative(&query, Some(&BTreeSet::from([good_shard])))
    );
    assert!(
        !index.native_compound_score_is_authoritative(&query, Some(&BTreeSet::from([bad_shard])))
    );
}

#[test]
fn native_compound_authority_preserves_pages_scores_and_min_score() {
    let fixture: Value = serde_json::from_str(include_str!(
        "../../../tools/fixtures/search-native-compound-ranking-compat.json"
    ))
    .unwrap();
    for definition in fixture["indices"].as_array().unwrap() {
        let name = definition["name"].as_str().unwrap();
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: name.into(),
                settings: definition["body"]["settings"].clone(),
                mappings: definition["body"]["mappings"].clone(),
            })
            .unwrap();
        let bulk = fixture["bulk"]
            .as_array()
            .unwrap()
            .iter()
            .find(|bulk| bulk["index"] == name)
            .unwrap();
        for doc in bulk["documents"].as_array().unwrap() {
            engine
                .index_document(IndexDocumentRequest {
                    index: name.into(),
                    id: doc["_id"].as_str().unwrap().into(),
                    source: doc["_source"].clone(),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec![name.into()],
            })
            .unwrap();
        for case in fixture["cases"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|case| case["steps"][0]["path"] == format!("/{name}/_search"))
        {
            let body = &case["steps"][0]["body"];
            let query = parse_query(&body["query"]).unwrap();
            if !matches!(query, Query::Bool { .. }) {
                continue;
            }
            let scores = {
                let store = engine.store.read().unwrap();
                let index = &store.indices[name];
                assert!(
                    index.native_compound_score_is_authoritative(&query, None),
                    "{}",
                    case["name"]
                );
                assert!(!index.native_query_needs_post_filter(&query, None));
                native_scores(index, &query, false)
            };
            let sorts = [
                vec![],
                vec![
                    serde_json::from_value::<SortSpec>(serde_json::json!({"field":"latency"}))
                        .unwrap(),
                ],
            ];
            for min_score in [None, Some(1.42)] {
                for sort in &sorts {
                    for from in 0..3 {
                        let mut envelope = serde_json::json!({"query":body["query"]});
                        if let Some(minimum) = min_score {
                            envelope["min_score"] = serde_json::json!(minimum);
                        }
                        let request: SearchRequest = serde_json::from_value(serde_json::json!({
                            "indices":[name],"query":envelope,"aggregations":{},"sort":sort,"from":from,"size":1,
                        })).unwrap();
                        let response = engine.search(request).unwrap();
                        let expected_count = scores
                            .values()
                            .filter(|&&score| min_score.map_or(true, |min| score >= min as f32))
                            .count();
                        assert_eq!(
                            response.total_hits as usize, expected_count,
                            "{} min={min_score:?}",
                            case["name"]
                        );
                        assert_eq!(response.hits.len(), usize::from(from < expected_count));
                        for hit in response.hits {
                            assert_eq!(
                                hit.score.to_bits(),
                                scores[&hit.metadata.id].to_bits(),
                                "{} min={min_score:?} sort={sort:?} from={from}",
                                case["name"]
                            );
                            assert!(min_score.map_or(true, |min| hit.score >= min as f32));
                        }
                    }
                }
            }
        }
    }
}

#[test]
fn native_compound_authority_covers_benchmark_ranking_shape() {
    let engine = TantivyEngine::default();
    engine
        .create_index(CreateIndexRequest {
            index: "benchmark-ranking".into(),
            settings: serde_json::json!({"number_of_shards":3}),
            mappings: serde_json::json!({
                "properties":{"title":{"type":"text"},"message":{"type":"text"},
                "service":{"type":"keyword"},"latency":{"type":"long"}}
            }),
        })
        .unwrap();
    for id in 0..96 {
        let service = ["checkout", "catalog", "payments", "search"][id % 4];
        let category = ["commerce", "search", "analytics"][id % 3];
        let term = [
            "alpha",
            "bravo",
            "charlie",
            "delta",
            "checkout",
            "catalog",
            "premium",
            "analytics",
        ][id % 8];
        engine.index_document(IndexDocumentRequest { index: "benchmark-ranking".into(), id: id.to_string(),
            source: serde_json::json!({"title":format!("{category} {service} summary {id}"),
                "message":format!("{term} service event {id}"),"service":service,"latency":10 + (id * 37) % 900}),
        }).unwrap();
    }
    engine
        .refresh(RefreshRequest {
            indices: vec!["benchmark-ranking".into()],
        })
        .unwrap();
    for (text, phrase) in [
        ("premium checkout", "premium checkout"),
        ("fast catalog", "fast catalog"),
        ("vector search", "premium checkout"),
        ("analytics dashboard", "fast catalog"),
    ] {
        let query_body = serde_json::json!({"bool":{"must":[{"multi_match":{
            "query":text,"fields":["title^2","message"],"type":"best_fields"}}],
            "should":[{"match_phrase":{"message":{"query":phrase,"slop":1}}},
                {"term":{"service":"checkout"}}],"minimum_should_match":1,
            "filter":[{"range":{"latency":{"lte":400}}}]}});
        let query = parse_query(&query_body).unwrap();
        let scores = {
            let store = engine.store.read().unwrap();
            let index = &store.indices["benchmark-ranking"];
            assert!(
                index.native_compound_score_is_authoritative(&query, None),
                "{text}"
            );
            native_scores(index, &query, false)
        };
        let request: SearchRequest = serde_json::from_value(serde_json::json!({
            "indices":["benchmark-ranking"],"query":query_body,"aggregations":{},"sort":[],"from":0,"size":100,
        })).unwrap();
        let response = engine.search(request).unwrap();
        assert_eq!(response.total_hits as usize, scores.len(), "{text}");
        for hit in response.hits {
            assert_eq!(
                hit.score.to_bits(),
                scores[&hit.metadata.id].to_bits(),
                "{text}"
            );
        }
    }
}

#[test]
fn native_msm_collectors_seek_horizons_and_deletions() {
    use tantivy::query::{EnableScoring, MinimumShouldMatchQuery};
    use tantivy::{DocSet, TERMINATED};
    let mut schema = tantivy::schema::Schema::builder();
    let field = schema.add_text_field("tags", tantivy::schema::STRING);
    let index = tantivy::Index::create_in_ram(schema.build());
    let mut writer = index.writer_with_num_threads(1, 15_000_000).unwrap();
    for doc in 0..8200 {
        let mut document = tantivy::Document::default();
        document.add_text(field, "alpha");
        // Buffered match at offset 2 must not leak into the next Count horizon.
        if [4096, 4098, 8193].contains(&doc) {
            document.add_text(field, "beta");
        }
        if doc == 8193 {
            document.add_text(field, "deleted");
        }
        writer.add_document(document).unwrap();
    }
    writer.commit().unwrap();
    let reader = index.reader().unwrap();
    let make_term = |text: &str, score| -> Box<dyn TantivyQueryTrait> {
        Box::new(ConstScoreQuery::new(
            Box::new(TermQuery::new(
                Term::from_field_text(field, text),
                tantivy::schema::IndexRecordOption::Basic,
            )),
            score,
        ))
    };
    let query =
        MinimumShouldMatchQuery::new(vec![make_term("alpha", 0.0), make_term("beta", 2.0)], 2);
    for deleted in [false, true] {
        if deleted {
            writer.delete_term(Term::from_field_text(field, "deleted"));
            writer.commit().unwrap();
            reader.reload().unwrap();
        }
        let searcher = reader.searcher();
        let expected = if deleted { 2 } else { 3 };
        assert_eq!(
            searcher.search(&query, &tantivy::collector::Count).unwrap(),
            expected
        );
        let hits = searcher.search(&query, &TopDocs::with_limit(10)).unwrap();
        assert_eq!(hits.len(), expected);
        assert!(hits.iter().all(|(score, _)| *score == 2.0));
        let boosted = tantivy::query::BoostQuery::new(Box::new(query.clone()), 3.0);
        assert!(searcher
            .search(&boosted, &TopDocs::with_limit(10))
            .unwrap()
            .iter()
            .all(|(score, _)| *score == 6.0));
        let weight = query
            .weight(EnableScoring::enabled_from_searcher(&searcher))
            .unwrap();
        for segment in searcher.segment_readers() {
            let mut scorer = weight.scorer(segment, 1.0).unwrap();
            assert_eq!(scorer.doc(), 4096);
            assert_eq!(scorer.seek(4096), 4096);
            assert_eq!(scorer.seek(5000), 8193);
            assert_eq!(scorer.score(), 2.0);
            assert_eq!(scorer.advance(), TERMINATED);
            assert_eq!(scorer.seek(TERMINATED), TERMINATED);
            let mut direct = weight.scorer(segment, 1.0).unwrap();
            assert_eq!(direct.seek(8193), 8193);
            assert_eq!(direct.count_including_deleted(), 1);
            assert!(weight.explain(segment, 0).is_err());
            assert!(weight.explain(segment, 4096).is_ok());
        }
        let duplicate =
            MinimumShouldMatchQuery::new((0..128).map(|_| make_term("alpha", 0.0)).collect(), 100);
        assert_eq!(
            searcher
                .search(&duplicate, &tantivy::collector::Count)
                .unwrap(),
            if deleted { 8199 } else { 8200 }
        );
        let sparse = MinimumShouldMatchQuery::new(vec![make_term("beta", 0.0)], 1);
        assert_eq!(
            searcher
                .search(&sparse, &tantivy::collector::Count)
                .unwrap(),
            expected
        );
        for impossible in [
            MinimumShouldMatchQuery::new(vec![], 1),
            MinimumShouldMatchQuery::new(vec![make_term("alpha", 1.0)], 2),
            MinimumShouldMatchQuery::new(
                vec![make_term("alpha", 1.0), make_term("absent", 1.0)],
                2,
            ),
        ] {
            assert_eq!(
                searcher
                    .search(&impossible, &tantivy::collector::Count)
                    .unwrap(),
                0
            );
        }
        assert!(MinimumShouldMatchQuery::new(vec![], 0)
            .weight(EnableScoring::enabled_from_searcher(&searcher))
            .is_err());
    }
}

#[test]
fn native_minimum_should_match_overlap_audit() {
    let mut rows = Vec::new();
    for shards in [1, 3] {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "msm-overlap".into(),
                settings: serde_json::json!({"number_of_shards": shards}),
                mappings: serde_json::json!({"properties": {
                    "tags": {"type": "keyword"}, "blocked": {"type": "keyword"}
                }}),
            })
            .unwrap();
        for mask in 0u32..32 {
            let tags = (0..5)
                .filter(|bit| mask & (1 << bit) != 0)
                .map(|bit| format!("t{bit}"))
                .collect::<Vec<_>>();
            engine.index_document(IndexDocumentRequest {
                index: "msm-overlap".into(), id: mask.to_string(),
                source: serde_json::json!({"tags": tags, "blocked": if mask == 31 {"yes"} else {"no"}}),
            }).unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["msm-overlap".into()],
            })
            .unwrap();
        let store = engine.store.read().unwrap();
        let index = &store.indices["msm-overlap"];
        for minimum in 0usize..=5 {
            let should = (0..5)
                .map(|bit| {
                    let term = serde_json::json!({"term": {"tags": format!("t{bit}")}});
                    if bit == 0 {
                        serde_json::json!({"bool": {"filter": [term]}})
                    } else {
                        term
                    }
                })
                .collect::<Vec<_>>();
            let query = parse_query(&serde_json::json!({"bool": {
                "must": [{"match_all": {}}],
                "filter": [{"match_all": {}}],
                "should": should, "minimum_should_match": minimum,
                "must_not": [{"term": {"blocked": "yes"}}]
            }}))
            .unwrap();
            let expected = (0u32..31)
                .filter(|mask| mask.count_ones() as usize >= minimum)
                .map(|mask| {
                    let score = 1 + (1..5).filter(|bit| mask & (1 << bit) != 0).count();
                    (mask.to_string(), score as f32)
                })
                .collect::<BTreeMap<_, _>>();
            let actual = native_scores(index, &query, false);
            let probe = native_scores(index, &query, true);
            assert_eq!(
                actual.keys().collect::<Vec<_>>(),
                expected.keys().collect::<Vec<_>>()
            );
            assert_eq!(
                probe, expected,
                "diagnostic max composition: shards={shards} minimum={minimum}"
            );
            assert_eq!(
                actual, expected,
                "native MSM: shards={shards} minimum={minimum}"
            );
            rows.push(serde_json::json!({"shards": shards, "minimum": minimum,
                "native": actual, "expected": expected, "probe": probe,
                "native_vs_additive": comparison(&actual, &expected)}));
        }
    }
    assert_eq!(rows.len(), 12);
    if let Some(path) = std::env::var_os("STEELSEARCH_NATIVE_MSM_OVERLAP_OUTPUT") {
        let file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
            .unwrap();
        serde_json::to_writer_pretty(file, &serde_json::json!({
            "diagnostic_only": true, "acceptance_established": false,
            "scope": "native composition; no HTTP min_score or paging; max probe still enumerates combinations",
            "rows": rows,
        })).unwrap();
    }
}

#[test]
fn native_compound_ranking_decomposition_audit() {
    let fixture: Value = serde_json::from_str(include_str!(
        "../../../tools/fixtures/search-native-compound-ranking-compat.json"
    ))
    .unwrap();
    let mut rows = Vec::new();
    for definition in fixture["indices"].as_array().unwrap() {
        let name = definition["name"].as_str().unwrap();
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: name.into(),
                settings: definition["body"]["settings"].clone(),
                mappings: definition["body"]["mappings"].clone(),
            })
            .unwrap();
        let bulk = fixture["bulk"]
            .as_array()
            .unwrap()
            .iter()
            .find(|bulk| bulk["index"] == name)
            .unwrap();
        for document in bulk["documents"].as_array().unwrap() {
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
        for case in fixture["cases"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|case| case["steps"][0]["path"] == format!("/{name}/_search"))
        {
            let request = &case["steps"][0]["body"];
            let query = parse_query(&request["query"]).unwrap();
            let native = native_scores(index, &query, false);
            let probe = native_scores(index, &query, true);
            let mut parts = Vec::new();
            if let Query::Bool { clauses } = &query {
                let groups = [
                    (&clauses.must, "must"),
                    (&clauses.should, "should"),
                    (&clauses.filter, "filter"),
                    (&clauses.must_not, "must_not"),
                ];
                let mut expected = BTreeMap::new();
                let scored_groups = groups
                    .iter()
                    .map(|(queries, occurrence)| {
                        let scored = queries
                            .iter()
                            .map(|child| native_scores(index, child, false))
                            .collect::<Vec<_>>();
                        parts.push(
                            serde_json::json!({"occurrence":occurrence,"native_scores":scored}),
                        );
                        scored
                    })
                    .collect::<Vec<_>>();
                for document in index.refreshed_documents_for_shards(None) {
                    let id = &document.metadata.id;
                    let matched_should = scored_groups[1]
                        .iter()
                        .filter(|hits| hits.contains_key(id))
                        .count();
                    if scored_groups[0].iter().all(|hits| hits.contains_key(id))
                        && scored_groups[2].iter().all(|hits| hits.contains_key(id))
                        && scored_groups[3].iter().all(|hits| !hits.contains_key(id))
                        && matched_should >= effective_bool_minimum_should_match(clauses) as usize
                    {
                        let score = scored_groups[0]
                            .iter()
                            .chain(&scored_groups[1])
                            .filter_map(|hits| hits.get(id))
                            .copied()
                            .sum::<f32>();
                        expected.insert(id.clone(), score);
                    }
                }
                assert_eq!(
                    native.keys().collect::<Vec<_>>(),
                    expected.keys().collect::<Vec<_>>(),
                    "native boolean membership: {}",
                    case["name"]
                );
                let delta = comparison(&native, &expected);
                assert!(
                    delta["max_absolute_difference"].as_f64().unwrap() < 1e-5,
                    "native additive scoring: {} {delta}",
                    case["name"]
                );
                let probe_delta = comparison(&probe, &expected);
                assert_eq!(
                    probe.keys().collect::<Vec<_>>(),
                    expected.keys().collect::<Vec<_>>()
                );
                assert!(
                    probe_delta["max_absolute_difference"].as_f64().unwrap() < 1e-5,
                    "native dismax additive scoring: {} {probe_delta}",
                    case["name"]
                );
                parts.push(
                    serde_json::json!({"additive_expected":expected,"native_vs_additive":delta,
                    "probe_vs_additive":probe_delta}),
                );
            }
            rows.push(serde_json::json!({
                "name":case["name"], "request":request,
                "native_query_scores_before_request_window_and_min_score":native,
                "native_dismax_probe_scores_before_request_window_and_min_score":probe,
                "components":parts,
                "static_requires_post_filter":query_requires_native_candidate_post_filter(&query),
                "static_allows_source_scan":query_allows_source_candidate_scan_for_native_post_filter(&query),
            }));
        }
    }
    assert_eq!(rows.len(), 60);
    if let Some(path) = std::env::var_os("STEELSEARCH_NATIVE_COMPOUND_AUDIT_OUTPUT") {
        let file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
            .unwrap();
        serde_json::to_writer_pretty(file, &serde_json::json!({
            "diagnostic_only":true, "acceptance_established":false,
            "scope":"native query composition only; request min_score, sorting and paging are not applied here",
            "rows":rows,
        })).unwrap();
    }
}

#[test]
fn native_exact_phrase_pages_preserve_native_scores_and_boosts() {
    for shards in [1, 3] {
        let engine = TantivyEngine::default();
        engine.create_index(CreateIndexRequest {index:"exact-phrase".into(),
            settings:serde_json::json!({"number_of_shards":shards}),
            mappings:serde_json::json!({"properties":{"body":{"type":"text"},"n":{"type":"long"}}}),
        }).unwrap();
        for (id, body) in [
            "alpha beta",
            "alpha beta alpha beta",
            "alpha gap beta",
            "other",
        ]
        .iter()
        .enumerate()
        {
            engine
                .index_document(IndexDocumentRequest {
                    index: "exact-phrase".into(),
                    id: id.to_string(),
                    source: serde_json::json!({"body":body,"n":id}),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["exact-phrase".into()],
            })
            .unwrap();
        let mut store = engine.store.write().unwrap();
        let index = store.indices.get_mut("exact-phrase").unwrap();
        let sorts = [
            vec![],
            vec![serde_json::from_value::<SortSpec>(serde_json::json!({"field":"n"})).unwrap()],
        ];
        for (text, slop) in [
            ("alpha beta", 0),
            ("alpha", 0),
            ("alpha beta", 1),
            ("alpha beta", 3),
            ("alpha alpha", 1),
        ] {
            for boost in [f64::from(f32::from_bits(1)), 0.5, 1.0, 2.0] {
                let query = parse_query(&serde_json::json!({"match_phrase":{"body":{"query":text,"boost":boost,"slop":slop}}})).unwrap();
                assert!(index.native_phrase_score_is_authoritative(&query, None));
                let scores = native_scores(index, &query, false);
                for sort in &sorts {
                    for from in 0..3 {
                        let (total, hits) = index
                            .search_hits_page_for_query_native_scoped(
                                "exact-phrase",
                                None,
                                &query,
                                sort,
                                from,
                                1,
                            )
                            .unwrap()
                            .unwrap();
                        assert_eq!(total as usize, scores.len());
                        assert_eq!(hits.len(), usize::from(from < scores.len()));
                        for hit in hits {
                            assert_eq!(hit.score.to_bits(),scores[&hit.metadata.id].to_bits(),
                                "shards={shards} text={text} boost={boost} sort={sort:?} from={from}");
                        }
                    }
                }
            }
        }
    }
}

#[test]
fn native_exact_phrase_full_sort_preserves_scores_for_null_and_array_values() {
    let engine = TantivyEngine::default();
    engine.create_index(CreateIndexRequest {index:"exact-phrase-full-sort".into(),settings:serde_json::json!({}),
        mappings:serde_json::json!({"properties":{"body":{"type":"text"},"latency":{"type":"long"},"service":{"type":"keyword"},"title":{"type":"text"}}}),
    }).unwrap();
    for (id, body, latency) in [
        ("exact", serde_json::json!("alpha beta"), 0),
        ("repeat", serde_json::json!("alpha beta alpha beta"), 300),
        ("null", serde_json::json!(null), 400),
        ("array", serde_json::json!(["alpha", "beta"]), 500),
    ] {
        engine.index_document(IndexDocumentRequest {index:"exact-phrase-full-sort".into(),id:id.into(),
            source:serde_json::json!({"body":body,"latency":latency,"service":"yes","title":"alpha beta"}),
        }).unwrap();
    }
    engine
        .refresh(RefreshRequest {
            indices: vec!["exact-phrase-full-sort".into()],
        })
        .unwrap();
    let store = engine.store.read().unwrap();
    let index = &store.indices["exact-phrase-full-sort"];
    let query = parse_query(&serde_json::json!({"match_phrase":{"body":"alpha beta"}})).unwrap();
    assert!(index.native_phrase_score_is_authoritative(&query, None));
    let expected = native_scores(index, &query, false);
    let sort = vec![
        serde_json::from_value::<SortSpec>(serde_json::json!({"field":"_score","order":"desc"}))
            .unwrap(),
        serde_json::from_value::<SortSpec>(
            serde_json::json!({"field":"latency","order":"asc","unmapped_type":"long"}),
        )
        .unwrap(),
    ];
    let (_total, hits) = index
        .search_hits_page_for_full_native_sort("exact-phrase-full-sort", None, &query, &sort, 0, 10)
        .unwrap()
        .unwrap();
    for hit in hits {
        assert_eq!(
            hit.score.to_bits(),
            expected[&hit.metadata.id].to_bits(),
            "{}",
            hit.metadata.id
        );
    }
    drop(store);
    let request: SearchRequest = serde_json::from_value(serde_json::json!({
        "indices":["exact-phrase-full-sort"],
        "query":{"query":{"match_phrase":{"body":"alpha beta"}}},
        "aggregations":{},"sort":[{"field":"_score","order":"desc"},{"field":"latency","order":"asc","unmapped_type":"long"}],"from":0,"size":10,
    })).unwrap();
    let response = engine.search(request).unwrap();
    for hit in response.hits {
        assert_eq!(
            hit.score.to_bits(),
            expected[&hit.metadata.id].to_bits(),
            "{}",
            hit.metadata.id
        );
    }
}

#[test]
fn native_exact_phrase_eligibility_rejects_unproven_options_and_values() {
    for options in [
        serde_json::json!({"analyzer":"keyword"}),
        serde_json::json!({"norms":false}),
        serde_json::json!({"position_increment_gap":"not-a-number"}),
        serde_json::json!({"index_options":"docs"}),
        serde_json::json!({"search_quote_analyzer":"simple"}),
        serde_json::json!({"similarity":"other"}),
    ] {
        let parsed: TantivyTextOptions = serde_json::from_value(options).unwrap();
        assert!(!parsed.supports_native_exact_phrase());
    }
    for value in [
        serde_json::json!("caf\u{e9}"),
        serde_json::json!({"body":"alpha"}),
    ] {
        assert!(!native_phrase_source_value_supported(&value));
    }
    for value in [
        serde_json::json!(5),
        serde_json::json!(true),
        serde_json::json!(["alpha", null, ["beta", 5, true]]),
    ] {
        assert!(native_phrase_source_value_supported(&value));
    }
    for gap in [
        serde_json::json!(0),
        serde_json::json!(1),
        serde_json::json!(5),
        serde_json::json!("100"),
    ] {
        let parsed: TantivyTextOptions =
            serde_json::from_value(serde_json::json!({"position_increment_gap":gap})).unwrap();
        assert!(parsed.supports_native_exact_phrase());
    }
    let engine = TantivyEngine::default();
    engine
        .create_index(CreateIndexRequest {
            index: "guard".into(),
            settings: serde_json::json!({}),
            mappings: serde_json::json!({"properties":{"body":{"type":"text"}}}),
        })
        .unwrap();
    engine
        .index_document(IndexDocumentRequest {
            index: "guard".into(),
            id: "1".into(),
            source: serde_json::json!({"body":"alpha beta"}),
        })
        .unwrap();
    engine
        .refresh(RefreshRequest {
            indices: vec!["guard".into()],
        })
        .unwrap();
    let mut store = engine.store.write().unwrap();
    let index = store.indices.get_mut("guard").unwrap();
    let query = parse_query(&serde_json::json!({"match_phrase":{"body":"alpha beta"}})).unwrap();
    assert!(index.native_phrase_score_is_authoritative(&query, None));
    for slop in [0, 1, 2, 100] {
        let query = parse_query(
            &serde_json::json!({"match_phrase":{"body":{"query":"alpha beta","slop":slop}}}),
        )
        .unwrap();
        assert!(index.native_phrase_score_is_authoritative(&query, None));
    }
    for body in [
        serde_json::json!({"query":"alpha beta","slop":4294967296u64}),
        serde_json::json!({"query":"alpha beta","analyzer":"keyword"}),
        serde_json::json!({"query":"","zero_terms_query":"all"}),
        serde_json::json!({"query":"alpha beta","boost":0.0}),
    ] {
        let query = parse_query(&serde_json::json!({"match_phrase":{"body":body}})).unwrap();
        assert!(!index.native_phrase_score_is_authoritative(&query, None));
    }
    index
        .schema
        .fields
        .iter_mut()
        .find(|field| field.name == "body")
        .unwrap()
        .text_options = None;
    assert!(!index.native_phrase_score_is_authoritative(&query, None));
}

#[test]
fn default_text_metadata_migration_keeps_legacy_schema_checks() {
    let create = CreateIndexRequest {
        index: "legacy-phrase".into(),
        settings: serde_json::json!({}),
        mappings: serde_json::json!({"properties":{"body":{"type":"text"}}}),
    };
    let current = map_opensearch_index_to_tantivy_schema(&create).unwrap();
    let mut legacy = current.clone();
    for field in &mut legacy.fields {
        field.text_options = None;
    }
    let old_hash = schema_hash(&create.index, &legacy).unwrap();
    assert_ne!(schema_hash(&create.index, &current).unwrap(), old_hash);
    assert!(matches_legacy_default_text_schema_hash(&create.index, &current, old_hash).unwrap());
    assert!(!matches_legacy_default_text_schema_hash("other-index", &current, old_hash).unwrap());
    let mut changed = current.clone();
    changed.fields[0].field_type = TantivyFieldType::Keyword;
    assert!(!matches_legacy_default_text_schema_hash(&create.index, &changed, old_hash).unwrap());
    let mut changed = current.clone();
    changed.fields[0].text_options.as_mut().unwrap().norms = Some(serde_json::json!(false));
    assert!(!matches_legacy_default_text_schema_hash(&create.index, &changed, old_hash).unwrap());
    let restored: TantivyIndexSchema =
        serde_json::from_value(serde_json::to_value(&current).unwrap()).unwrap();
    assert_eq!(restored, current);
    let engine = TantivyEngine::default();
    engine
        .create_index_from_schema(create.index.clone(), legacy)
        .unwrap();
    engine
        .index_document(IndexDocumentRequest {
            index: create.index.clone(),
            id: "1".into(),
            source: serde_json::json!({"body":"alpha beta alpha beta"}),
        })
        .unwrap();
    let path = std::env::temp_dir().join(format!(
        "steel-native-phrase-migration-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    engine.persist_shard_state(&create.index, &path).unwrap();
    let recovered = TantivyEngine::default();
    recovered
        .recover_index_from_manifest(&create.index, current.clone(), &path)
        .unwrap();
    let migrated = recovered.shard_manifest(&create.index).unwrap();
    assert_eq!(
        migrated.schema_hash,
        schema_hash(&create.index, &current).unwrap()
    );
    assert!(TantivyEngine::default()
        .recover_index_from_manifest(&create.index, changed, &path)
        .is_err());
    recovered.persist_shard_state(&create.index, &path).unwrap();
    TantivyEngine::default()
        .recover_index_from_manifest(&create.index, current, &path)
        .unwrap();
    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn native_exact_phrase_value_guard_follows_refresh() {
    let engine = TantivyEngine::default();
    engine
        .create_index(CreateIndexRequest {
            index: "phrase-refresh".into(),
            settings: serde_json::json!({}),
            mappings: serde_json::json!({"properties":{"body":{"type":"text"}}}),
        })
        .unwrap();
    let query = parse_query(&serde_json::json!({"match_phrase":{"body":"alpha beta"}})).unwrap();
    for (body, expected) in [
        (serde_json::json!("alpha beta"), true),
        (serde_json::json!("alpha caf\u{e9}"), false),
        (serde_json::json!(5), false),
        (serde_json::json!("alpha beta alpha beta"), true),
    ] {
        engine
            .index_document(IndexDocumentRequest {
                index: "phrase-refresh".into(),
                id: "1".into(),
                source: serde_json::json!({"body":body}),
            })
            .unwrap();
        engine
            .refresh(RefreshRequest {
                indices: vec!["phrase-refresh".into()],
            })
            .unwrap();
        let store = engine.store.read().unwrap();
        assert_eq!(
            store.indices["phrase-refresh"].native_phrase_score_is_authoritative(&query, None),
            expected
        );
    }
}

#[test]
fn native_text_metadata_preserves_accepted_option_input_shapes() {
    let fixture: Value = serde_json::from_str(include_str!(
        "../../../tools/fixtures/search-native-text-option-inputs-compat.json"
    ))
    .unwrap();
    for definition in fixture["indices"].as_array().unwrap() {
        let request = CreateIndexRequest {
            index: definition["name"].as_str().unwrap().into(),
            settings: definition["body"]["settings"].clone(),
            mappings: definition["body"]["mappings"].clone(),
        };
        let schema = map_opensearch_index_to_tantivy_schema(&request).unwrap();
        let options = schema
            .fields
            .iter()
            .find(|field| field.name == "body")
            .unwrap()
            .text_options
            .as_ref()
            .unwrap();
        let serialized = serde_json::to_value(options).unwrap();
        for (key, value) in serialized.as_object().unwrap() {
            assert_eq!(value, &request.mappings["properties"]["body"][key]);
        }
        assert!(!options.supports_native_exact_phrase());
        TantivyEngine::default().create_index(request).unwrap();
    }
    assert_eq!(
        std::mem::size_of::<Option<Box<TantivyTextOptions>>>(),
        std::mem::size_of::<usize>()
    );
}

#[test]
fn native_pre_tokenized_gap_preserves_term_scores_and_norms() {
    use tantivy::collector::Count;
    use tantivy::schema::{IndexRecordOption, Schema, TEXT};
    use tantivy::tokenizer::PreTokenizedString;
    use tantivy::{DocSet, Postings};
    let mut builder = Schema::builder();
    let field = builder.add_text_field("body", TEXT);
    let index = tantivy::Index::create_in_ram(builder.build());
    let mut writer = index.writer(15_000_000).unwrap();
    let mut contiguous = tantivy::Document::default();
    contiguous.add_text(field, "alpha beta");
    writer.add_document(contiguous).unwrap();

    let mut analyzer = index.tokenizer_for_field(field).unwrap();
    let mut stream = analyzer.token_stream("alpha beta");
    let mut tokens = Vec::new();
    while stream.advance() {
        tokens.push(stream.token().clone());
    }
    assert_eq!(tokens.len(), 2);
    tokens[1].position = 101;
    let mut spaced = tantivy::Document::default();
    spaced.add_pre_tokenized_text(
        field,
        PreTokenizedString {
            text: "alpha beta".into(),
            tokens,
        },
    );
    writer.add_document(spaced).unwrap();
    let mut default_array = tantivy::Document::default();
    default_array.add_text(field, "alpha");
    default_array.add_text(field, "beta");
    writer.add_document(default_array).unwrap();
    writer.commit().unwrap();
    let reader = index.reader().unwrap();
    let searcher = reader.searcher();
    assert_eq!(searcher.segment_readers().len(), 1);
    let segment = searcher.segment_reader(0);
    let inverted = segment.inverted_index(field).unwrap();
    assert_eq!(inverted.total_num_tokens(), 6);
    let norms = segment.get_fieldnorms_reader(field).unwrap();
    for doc in 0..3 {
        assert_eq!(norms.fieldnorm(doc), 2);
    }
    let beta = Term::from_field_text(field, "beta");
    let mut postings = inverted
        .read_postings(&beta, IndexRecordOption::WithFreqsAndPositions)
        .unwrap()
        .unwrap();
    for (doc, expected) in [(0, 1), (1, 101), (2, 2)] {
        assert_eq!(postings.seek(doc), doc);
        let mut positions = Vec::new();
        postings.positions(&mut positions);
        assert_eq!(positions, vec![expected]);
    }
    let query = tantivy::query::TermQuery::new(beta, IndexRecordOption::WithFreqs);
    let hits = searcher.search(&query, &TopDocs::with_limit(3)).unwrap();
    assert_eq!(hits.len(), 3);
    assert!(hits
        .iter()
        .all(|hit| hit.0.to_bits() == hits[0].0.to_bits()));
    for (terms, cases) in [
        (
            ["alpha", "beta"],
            vec![(0, 1), (1, 2), (99, 2), (100, 3), (101, 3)],
        ),
        (
            ["beta", "alpha"],
            vec![(0, 0), (1, 0), (2, 1), (3, 2), (101, 2), (102, 3)],
        ),
    ] {
        for (slop, expected) in cases {
            let query = PhraseQuery::new_with_offset_and_slop(
                terms
                    .iter()
                    .enumerate()
                    .map(|(offset, token)| (offset, Term::from_field_text(field, token)))
                    .collect(),
                slop,
            );
            assert_eq!(
                searcher.search(&query, &Count).unwrap(),
                expected,
                "terms={terms:?} slop={slop}"
            );
        }
    }
}

#[test]
fn native_phrase_frequency_and_position_audit() {
    use tantivy::{DocSet, Postings};
    let fixture: Value = serde_json::from_str(include_str!(
        "../../../tools/fixtures/search-native-phrase-explain-compat.json"
    ))
    .unwrap();
    let mut rows = Vec::new();
    for definition in fixture["indices"].as_array().unwrap() {
        let engine = TantivyEngine::default();
        let name = definition["name"].as_str().unwrap();
        engine
            .create_index(CreateIndexRequest {
                index: name.into(),
                settings: definition["body"]["settings"].clone(),
                mappings: definition["body"]["mappings"].clone(),
            })
            .unwrap();
        let bulk = fixture["bulk"]
            .as_array()
            .unwrap()
            .iter()
            .find(|bulk| bulk["index"] == name)
            .unwrap();
        for document in bulk["documents"].as_array().unwrap() {
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
        let states = if index.documents.shard_count == 1 {
            index.search_state.iter().collect::<Vec<_>>()
        } else {
            index
                .shard_search_states_for(None)
                .map(|(_, state)| state)
                .collect()
        };
        for case in fixture["cases"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|case| case["steps"][0]["path"] == format!("/{name}/_search"))
        {
            let query = parse_query(&case["steps"][0]["body"]["query"]).unwrap();
            let mut hits = BTreeMap::new();
            for state in &states {
                let native = build_tantivy_query(state, &query).unwrap().unwrap();
                let probe = compose_native_probe(state, &query);
                let field = state.fields["body"].field;
                for (score, address) in state
                    .searcher
                    .search(native.as_ref(), &TopDocs::with_limit(100))
                    .unwrap()
                {
                    let id = state
                        .document_id_for_address(&state.searcher, address)
                        .unwrap();
                    let segment = state.searcher.segment_reader(address.segment_ord);
                    let inverted = segment.inverted_index(field).unwrap();
                    let mut positions = BTreeMap::new();
                    for token in ["alpha", "beta"] {
                        let mut postings = inverted
                            .read_postings(
                                &Term::from_field_text(field, token),
                                tantivy::schema::IndexRecordOption::WithFreqsAndPositions,
                            )
                            .unwrap()
                            .unwrap();
                        assert_eq!(postings.seek(address.doc_id), address.doc_id);
                        let mut values = Vec::new();
                        postings.positions(&mut values);
                        positions.insert(token, values);
                    }
                    assert!(score.is_finite() && score > 0.0);
                    assert!(hits.insert(id.to_string(), serde_json::json!({
                        "score":score, "positions":positions,
                        "native_explanation":native.explain(&state.searcher,address).unwrap(),
                        "probe_explanation":probe.explain(&state.searcher,address).unwrap(),
                    })).is_none());
                }
            }
            assert!(hits.contains_key("exact") && hits.contains_key("repeat"));
            rows.push(serde_json::json!({"name":case["name"],"hits":hits}));
        }
    }
    assert_eq!(rows.len(), 28);
    if let Some(path) = std::env::var_os("STEELSEARCH_NATIVE_PHRASE_AUDIT_OUTPUT") {
        let file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
            .unwrap();
        serde_json::to_writer_pretty(
            file,
            &serde_json::json!({
                "diagnostic_only":true,"acceptance_established":false,"rows":rows,
            }),
        )
        .unwrap();
    }
}

#[test]
fn native_repeated_phrase_frequency_audit() {
    use tantivy::{DocSet, Postings};
    let fixture: Value = serde_json::from_str(include_str!(
        "../../../tools/fixtures/search-native-phrase-frequency-compat.json"
    ))
    .unwrap();
    let reference: Value = serde_json::from_str(include_str!(
        "../../../tools/fixtures/search-native-phrase-frequency-reference.json"
    ))
    .unwrap();
    let mut rows = Vec::new();
    for definition in fixture["indices"].as_array().unwrap() {
        let name = definition["name"].as_str().unwrap();
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: name.into(),
                settings: definition["body"]["settings"].clone(),
                mappings: definition["body"]["mappings"].clone(),
            })
            .unwrap();
        let bulk = fixture["bulk"]
            .as_array()
            .unwrap()
            .iter()
            .find(|bulk| bulk["index"] == name)
            .unwrap();
        for document in bulk["documents"].as_array().unwrap() {
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
        let states = if index.documents.shard_count == 1 {
            index.search_state.iter().collect::<Vec<_>>()
        } else {
            index
                .shard_search_states_for(None)
                .map(|(_, state)| state)
                .collect()
        };
        for case in fixture["cases"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|case| case["steps"][0]["path"] == format!("/{name}/_search"))
        {
            let body = &case["steps"][0]["body"]["query"];
            let tokens = body["match_phrase"]["body"]["query"]
                .as_str()
                .unwrap()
                .split_whitespace()
                .collect::<BTreeSet<_>>();
            let query = parse_query(body).unwrap();
            if body["match_phrase"]["body"]["slop"].as_u64().unwrap() > 0 {
                assert!(index.native_phrase_score_is_authoritative(&query, None));
            }
            let mut hits = BTreeMap::new();
            for state in &states {
                let native = build_tantivy_query(state, &query).unwrap().unwrap();
                let field = state.fields["body"].field;
                for (score, address) in state
                    .searcher
                    .search(native.as_ref(), &TopDocs::with_limit(100))
                    .unwrap()
                {
                    let id = state
                        .document_id_for_address(&state.searcher, address)
                        .unwrap();
                    let inverted = state
                        .searcher
                        .segment_reader(address.segment_ord)
                        .inverted_index(field)
                        .unwrap();
                    let mut positions = BTreeMap::new();
                    for token in &tokens {
                        let mut postings = inverted
                            .read_postings(
                                &Term::from_field_text(field, token),
                                IndexRecordOption::WithFreqsAndPositions,
                            )
                            .unwrap()
                            .unwrap();
                        if postings.doc() < address.doc_id {
                            postings.seek(address.doc_id);
                        }
                        assert_eq!(postings.doc(), address.doc_id);
                        let mut values = Vec::new();
                        postings.positions(&mut values);
                        positions.insert(*token, values);
                    }
                    assert!(score.is_finite() && score > 0.0);
                    assert!(hits
                        .insert(
                            id.to_owned(),
                            serde_json::json!({
                                "score": score, "positions": positions,
                                "explanation": native.explain(&state.searcher, address).unwrap(),
                            })
                        )
                        .is_none());
                }
            }
            assert!(!hits.is_empty(), "{}", case["name"]);
            let ordered_tokens = body["match_phrase"]["body"]["query"]
                .as_str()
                .unwrap()
                .split_whitespace()
                .collect::<Vec<_>>();
            let term_ids = ordered_tokens
                .iter()
                .map(|token| {
                    tokens
                        .iter()
                        .position(|candidate| candidate == token)
                        .unwrap()
                })
                .collect::<Vec<_>>();
            let offsets = (0..ordered_tokens.len() as u32).collect::<Vec<_>>();
            let mut matcher = phrase_positions::Matcher::new(&term_ids, &offsets);
            let slop = body["match_phrase"]["body"]["slop"].as_u64().unwrap() as u32;
            let mut matched = BTreeMap::new();
            let mut scored = BTreeMap::new();
            for state in &states {
                let field = state.fields["body"].field;
                let phrase = super::native_phrase::NativePhraseQuery::new(
                    ordered_tokens
                        .iter()
                        .enumerate()
                        .map(|(offset, token)| (offset, Term::from_field_text(field, token)))
                        .collect(),
                    slop,
                )
                .unwrap();
                let normalized =
                    state
                        .bm25_field_statistics
                        .wrap(Box::new(phrase), field, &state.searcher);
                let boosted = BoostQuery::new(
                    normalized,
                    body["match_phrase"]["body"]["boost"].as_f64().unwrap() as f32,
                );
                let scores = state
                    .searcher
                    .search(&boosted, &TopDocs::with_limit(100))
                    .unwrap();
                assert_eq!(
                    state.searcher.search(&boosted, &Count).unwrap(),
                    scores.len()
                );
                let seek_scores = super::native_bm25::score_addresses(
                    &state.searcher,
                    &boosted,
                    scores.iter().map(|(_, address)| *address).collect(),
                )
                .unwrap();
                assert_eq!(scores, seek_scores);
                for (score, address) in scores {
                    let id = state
                        .document_id_for_address(&state.searcher, address)
                        .unwrap();
                    let explanation =
                        serde_json::to_value(boosted.explain(&state.searcher, address).unwrap())
                            .unwrap();
                    fn find_frequency(value: &Value) -> Option<f64> {
                        if value["description"] == "phraseFreq" {
                            return value["value"].as_f64();
                        }
                        value["details"].as_array()?.iter().find_map(find_frequency)
                    }
                    let frequency = find_frequency(&explanation).unwrap() as f32;
                    assert!(scored
                        .insert(
                            id.to_owned(),
                            serde_json::json!({
                                "score":score, "frequency":frequency, "explanation":explanation,
                            })
                        )
                        .is_none());
                }
                // Use native term conjunction, not the known-incomplete sloppy PhraseScorer.
                let conjunction = BooleanQuery::new(
                    tokens
                        .iter()
                        .map(|token| {
                            (
                                Occur::Must,
                                Box::new(TermQuery::new(
                                    Term::from_field_text(field, token),
                                    IndexRecordOption::Basic,
                                )) as Box<dyn TantivyQueryTrait>,
                            )
                        })
                        .collect(),
                );
                for address in state
                    .searcher
                    .search(&conjunction, &DocSetCollector)
                    .unwrap()
                {
                    let inverted = state
                        .searcher
                        .segment_reader(address.segment_ord)
                        .inverted_index(field)
                        .unwrap();
                    let positions = ordered_tokens
                        .iter()
                        .map(|token| {
                            let mut postings = inverted
                                .read_postings(
                                    &Term::from_field_text(field, token),
                                    IndexRecordOption::WithFreqsAndPositions,
                                )
                                .unwrap()
                                .unwrap();
                            if postings.doc() < address.doc_id {
                                postings.seek(address.doc_id);
                            }
                            assert_eq!(postings.doc(), address.doc_id);
                            let mut positions = Vec::new();
                            postings.positions(&mut positions);
                            positions
                        })
                        .collect::<Vec<_>>();
                    let frequency = matcher.frequency(&positions, slop);
                    if frequency > 0.0 {
                        let id = state
                            .document_id_for_address(&state.searcher, address)
                            .unwrap();
                        assert!(matched.insert(id.to_owned(), frequency).is_none());
                    }
                }
            }
            let expected = reference["rows"]
                .as_array()
                .unwrap()
                .iter()
                .find(|row| row["name"] == case["name"])
                .unwrap()["hits"]
                .as_object()
                .unwrap();
            assert_eq!(
                matched.keys().collect::<BTreeSet<_>>(),
                expected.keys().collect::<BTreeSet<_>>(),
                "{}",
                case["name"]
            );
            assert_eq!(
                scored.keys().collect::<BTreeSet<_>>(),
                expected.keys().collect::<BTreeSet<_>>(),
                "{}",
                case["name"]
            );
            for (id, frequency) in &matched {
                assert_eq!(
                    *frequency,
                    expected[id]["frequencies"][0].as_f64().unwrap() as f32,
                    "{} {id}",
                    case["name"]
                );
                assert_eq!(scored[id]["frequency"].as_f64().unwrap() as f32, *frequency);
            }
            if body["match_phrase"]["body"]["slop"] == 0 {
                let expected = reference["rows"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .find(|row| row["name"] == case["name"])
                    .unwrap()["hits"]
                    .as_object()
                    .unwrap();
                assert_eq!(
                    hits.keys().collect::<BTreeSet<_>>(),
                    expected.keys().collect::<BTreeSet<_>>()
                );
                fn frequencies(explanation: &Value, values: &mut Vec<f64>) {
                    if explanation["description"]
                        .as_str()
                        .unwrap()
                        .starts_with("freq,")
                    {
                        values.push(explanation["value"].as_f64().unwrap());
                    }
                    if let Some(details) = explanation["details"].as_array() {
                        for detail in details {
                            frequencies(detail, values);
                        }
                    }
                }
                for (id, hit) in &hits {
                    let mut actual = Vec::new();
                    frequencies(&hit["explanation"], &mut actual);
                    let expected = expected[id]["frequencies"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .map(|value| value.as_f64().unwrap())
                        .collect::<Vec<_>>();
                    assert_eq!(actual, expected, "{} {id}", case["name"]);
                }
            }
            rows.push(serde_json::json!({"name":case["name"], "hits":hits, "matcher_frequencies":matched, "scorer_hits":scored}));
        }
    }
    assert_eq!(rows.len(), 120);
    if let Some(path) = std::env::var_os("STEELSEARCH_NATIVE_REPEATED_PHRASE_OUTPUT") {
        let file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
            .unwrap();
        serde_json::to_writer_pretty(
            file,
            &serde_json::json!({
                "diagnostic_only":true, "acceptance_established":false, "rows":rows,
            }),
        )
        .unwrap();
    }
}

// Diagnostic composition only: no production routing or acceptance tolerance changes.
fn compose_native_probe(state: &TantivySearchState, query: &Query) -> Box<dyn TantivyQueryTrait> {
    match query {
        Query::Bool { clauses } if effective_bool_minimum_should_match(clauses) >= 1 => {
            let mut built = clauses
                .must
                .iter()
                .map(|query| (Occur::Must, compose_native_probe(state, query)))
                .collect::<Vec<_>>();
            built.extend(clauses.filter.iter().map(|query| {
                (
                    Occur::Must,
                    Box::new(ConstScoreQuery::new(
                        compose_native_probe(state, query),
                        0.0,
                    )) as Box<dyn TantivyQueryTrait>,
                )
            }));
            built.extend(
                clauses
                    .must_not
                    .iter()
                    .map(|query| (Occur::MustNot, compose_native_probe(state, query))),
            );
            let minimum = effective_bool_minimum_should_match(clauses) as usize;
            let optional: Box<dyn TantivyQueryTrait> = if minimum == 1 {
                Box::new(BooleanQuery::new(
                    clauses
                        .should
                        .iter()
                        .map(|query| (Occur::Should, compose_native_probe(state, query)))
                        .collect(),
                ))
            } else {
                // Each matching branch scores every matching child once; max avoids duplicate sums.
                let alternatives = query_index_combinations(clauses.should.len(), minimum)
                    .into_iter()
                    .map(|combination| {
                        Box::new(BooleanQuery::new(
                            clauses
                                .should
                                .iter()
                                .enumerate()
                                .map(|(i, query)| {
                                    let occur = if combination.contains(&i) {
                                        Occur::Must
                                    } else {
                                        Occur::Should
                                    };
                                    (occur, compose_native_probe(state, query))
                                })
                                .collect(),
                        )) as Box<dyn TantivyQueryTrait>
                    })
                    .collect();
                Box::new(DisjunctionMaxQuery::new(alternatives))
            };
            built.push((Occur::Must, optional));
            Box::new(BooleanQuery::new(built))
        }
        _ => build_tantivy_query(state, query).unwrap().unwrap(),
    }
}

pub(super) fn native_scores(
    index: &StoredIndex,
    query: &Query,
    probe: bool,
) -> BTreeMap<String, f32> {
    let states = if index.documents.shard_count <= 1 {
        index.search_state.iter().collect::<Vec<_>>()
    } else {
        index
            .shard_search_states_for(None)
            .map(|(_, state)| state)
            .collect()
    };
    let mut result = BTreeMap::new();
    for state in states {
        let built = if probe {
            compose_native_probe(state, query)
        } else {
            build_tantivy_query(state, query)
                .unwrap()
                .expect("audit query has a native builder")
        };
        for (score, address) in state
            .searcher
            .search(built.as_ref(), &TopDocs::with_limit(100))
            .unwrap()
        {
            let id = state
                .document_id_for_address(&state.searcher, address)
                .unwrap();
            assert!(score.is_finite());
            assert!(result.insert(id.to_string(), score).is_none());
        }
    }
    result
}

fn comparison(left: &BTreeMap<String, f32>, right: &BTreeMap<String, f32>) -> Value {
    let missing = right
        .keys()
        .filter(|id| !left.contains_key(*id))
        .collect::<Vec<_>>();
    let extra = left
        .keys()
        .filter(|id| !right.contains_key(*id))
        .collect::<Vec<_>>();
    let mut max_absolute = 0.0_f64;
    let mut max_relative = 0.0_f64;
    let mut bit_differences = 0;
    for (id, &actual) in left {
        if let Some(&expected) = right.get(id) {
            let difference = (f64::from(actual) - f64::from(expected)).abs();
            max_absolute = max_absolute.max(difference);
            if expected != 0.0 {
                max_relative = max_relative.max(difference / f64::from(expected).abs());
            }
            bit_differences += usize::from(actual.to_bits() != expected.to_bits());
        }
    }
    serde_json::json!({"missing":missing, "extra":extra, "bit_differences":bit_differences,
        "max_absolute_difference":max_absolute, "max_relative_difference_nonzero":max_relative})
}

#[test]
fn native_ranking_leaf_and_bool_audit() {
    let documents = vec![
        serde_json::json!({"_id":"exact", "_source":{"title":"alpha beta", "body":"alpha beta", "service":"yes", "latency":0}}),
        serde_json::json!({"_id":"gap", "_source":{"title":"alpha", "body":"alpha gap beta", "service":"yes", "latency":100}}),
        serde_json::json!({"_id":"reverse", "_source":{"title":"beta", "body":"beta alpha", "service":"other", "latency":200}}),
        serde_json::json!({"_id":"repeat", "_source":{"title":"alpha", "body":"alpha beta alpha beta", "service":"yes", "latency":300}}),
        serde_json::json!({"_id":"null", "_source":{"title":"other", "body":null, "service":"yes", "latency":400}}),
        serde_json::json!({"_id":"array", "_source":{"title":"alpha", "body":["alpha", "beta"], "service":"other", "latency":500}}),
        serde_json::json!({"_id":"sparse", "_source":{"body":"alpha beta", "service":"other", "latency":600}}),
        serde_json::json!({"_id":"wide-gap", "_source":{"title":"alpha", "body":"alpha gap gap beta", "service":"other", "latency":700}}),
    ];
    let multi = serde_json::json!({"multi_match":{"query":"alpha beta", "fields":["title^2", "body"], "type":"best_fields"}});
    let phrase = serde_json::json!({"match_phrase":{"body":{"query":"alpha beta", "slop":1}}});
    let full = serde_json::json!({"bool":{
        "must":[multi.clone()], "should":[phrase.clone(), {"term":{"service":"yes"}}],
        "minimum_should_match":1, "filter":[{"range":{"latency":{"lte":600}}}]
    }});
    let queries = vec![
        (
            "match-title",
            serde_json::json!({"match":{"title":"alpha beta"}}),
        ),
        (
            "match-body",
            serde_json::json!({"match":{"body":"alpha beta"}}),
        ),
        ("multi-match", multi),
        (
            "phrase-exact",
            serde_json::json!({"match_phrase":{"body":"alpha beta"}}),
        ),
        ("phrase-slop", phrase),
        (
            "phrase-boost",
            serde_json::json!({"match_phrase":{"body":{"query":"alpha beta", "slop":1, "boost":2}}}),
        ),
        (
            "bool-overlap",
            serde_json::json!({"bool":{
                "must":{"match_all":{}},
                "should":[{"term":{"service":"yes"}}, {"range":{"latency":{"lte":300}}}],
                "minimum_should_match":1
            }}),
        ),
        ("full-ranking", full),
    ];
    let mut rows = Vec::new();
    let mut fixture_indices = Vec::new();
    let mut fixture_bulk = Vec::new();
    let mut fixture_cases = Vec::new();
    for shards in [1, 3] {
        let engine = TantivyEngine::default();
        let name = format!("native-ranking-audit-{shards}");
        let settings = serde_json::json!({"number_of_shards":shards,"number_of_replicas":0,"refresh_interval":"-1"});
        let mappings = serde_json::json!({"properties":{
            "title":{"type":"text"}, "body":{"type":"text"},
            "service":{"type":"keyword"}, "latency":{"type":"long"}
        }});
        engine
            .create_index(CreateIndexRequest {
                index: name.clone(),
                settings: settings.clone(),
                mappings: mappings.clone(),
            })
            .unwrap();
        for document in &documents {
            engine
                .index_document(IndexDocumentRequest {
                    index: name.clone(),
                    id: document["_id"].as_str().unwrap().into(),
                    source: document["_source"].clone(),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec![name.clone()],
            })
            .unwrap();
        let store = engine.store.read().unwrap();
        let index = &store.indices[&name];
        fixture_indices.push(
            serde_json::json!({"name":name,"body":{"settings":settings,"mappings":mappings}}),
        );
        fixture_bulk.push(serde_json::json!({"index":name,"documents":documents}));
        for (case, body) in &queries {
            let query = parse_query(body).unwrap();
            let source = index
                .refreshed_documents_for_shards(None)
                .into_iter()
                .filter_map(|document| {
                    index
                        .score_document_query(&query, document)
                        .unwrap()
                        .map(|score| (document.metadata.id.clone(), score))
                })
                .collect::<BTreeMap<_, _>>();
            let native = native_scores(index, &query, false);
            let probe = native_scores(index, &query, true);
            if *case == "bool-overlap" {
                assert_eq!(source["exact"], 3.0);
                assert_eq!(probe["exact"], 3.0);
                assert_eq!(
                    native["exact"], 3.0,
                    "native optional group must not double count"
                );
                assert_eq!(native, source);
                assert_eq!(probe, source);
            }
            rows.push(serde_json::json!({"shards":shards,"case":case,"query":body,
                "requires_source_post_filter":query_requires_native_candidate_post_filter(&query),
                "native_vs_source":comparison(&native,&source),"probe_vs_source":comparison(&probe,&source),
                "native":native,"source":source,"probe":probe}));
            fixture_cases.push(serde_json::json!({"name":format!("{shards}-{case}"),
                "area":"search","family":"ranking","extract":"search_scores",
                "steps":[{"method":"POST","path":format!("/{name}/_search"),
                    "body":{"size":100,"query":body},"expected_status":200}]}));
        }
    }
    assert_eq!(rows.len(), 16);
    if let Some(path) = std::env::var_os("STEELSEARCH_NATIVE_RANKING_AUDIT_OUTPUT") {
        let file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
            .unwrap();
        serde_json::to_writer_pretty(file, &serde_json::json!({
            "diagnostic_only":true,"acceptance_established":false,"rows":rows,
            "reference_fixture":{"indices":fixture_indices,"bulk":fixture_bulk,"cases":fixture_cases}
        })).unwrap();
    }
}

#[test]
fn native_two_of_three_compound_scores_match_lucene_10() {
    let fixture: Value = serde_json::from_str(include_str!(
        "../../../tools/fixtures/search-native-compound-ranking-compat.json"
    ))
    .unwrap();
    let definition = fixture["indices"]
        .as_array()
        .unwrap()
        .iter()
        .find(|definition| definition["name"] == "native-ranking-audit-1")
        .unwrap();
    let engine = TantivyEngine::default();
    engine
        .create_index(CreateIndexRequest {
            index: "native-ranking-audit-1".into(),
            settings: definition["body"]["settings"].clone(),
            mappings: definition["body"]["mappings"].clone(),
        })
        .unwrap();
    let bulk = fixture["bulk"]
        .as_array()
        .unwrap()
        .iter()
        .find(|batch| batch["index"] == "native-ranking-audit-1")
        .unwrap();
    for document in bulk["documents"].as_array().unwrap() {
        engine
            .index_document(IndexDocumentRequest {
                index: "native-ranking-audit-1".into(),
                id: document["_id"].as_str().unwrap().into(),
                source: document["_source"].clone(),
            })
            .unwrap();
    }
    engine
        .refresh(RefreshRequest {
            indices: vec!["native-ranking-audit-1".into()],
        })
        .unwrap();
    let store = engine.store.read().unwrap();
    let index = &store.indices["native-ranking-audit-1"];
    for (case_name, expected) in [
        (
            "1-full-both-field",
            vec![
                ("exact", 2.135_554_3_f32),
                ("gap", 1.394_947_6_f32),
                ("repeat", 1.430_176_7_f32),
            ],
        ),
        (
            "1-full-two-of-three-field",
            vec![
                ("exact", 2.168_429_4_f32),
                ("gap", 1.423_072_1_f32),
                ("repeat", 1.465_771_3_f32),
                ("sparse", 0.164_374_26_f32),
            ],
        ),
    ] {
        let body = fixture["cases"]
            .as_array()
            .unwrap()
            .iter()
            .find(|case| case["name"] == case_name)
            .unwrap()["steps"][0]["body"]
            .clone();
        let query = parse_query(&body["query"]).unwrap();
        assert!(index.native_query_score_is_authoritative(&query, None));
        let scores = native_scores(index, &query, false);
        for (id, expected) in expected {
            assert_eq!(scores[id].to_bits(), expected.to_bits(), "{case_name}:{id}");
        }
    }
}

#[test]
fn native_minimum_one_preserves_matches_and_scores_across_overlapping_shoulds() {
    for shards in [1, 3] {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "native-minimum-one".into(),
                settings: serde_json::json!({"number_of_shards":shards}),
                mappings: serde_json::json!({"properties":{
                    "a":{"type":"keyword"}, "b":{"type":"keyword"},
                    "c":{"type":"keyword"}, "allowed":{"type":"keyword"}
                }}),
            })
            .unwrap();
        for mask in 0..16 {
            engine
                .index_document(IndexDocumentRequest {
                    index: "native-minimum-one".into(),
                    id: mask.to_string(),
                    source: serde_json::json!({"a":if mask & 1 != 0 {"yes"} else {"no"},
                    "b":if mask & 2 != 0 {"yes"} else {"no"},
                    "c":if mask & 4 != 0 {"yes"} else {"no"},
                    "allowed":if mask & 8 != 0 {"yes"} else {"no"}}),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["native-minimum-one".into()],
            })
            .unwrap();
        let store = engine.store.read().unwrap();
        let index = &store.indices["native-minimum-one"];
        let term = |field: &str| Query::Term {
            field: field.into(),
            value: serde_json::json!("yes"),
            case_insensitive: false,
        };
        for count in 1..=4 {
            for required in [false, true] {
                for filtered in [false, true] {
                    for excluded in [false, true] {
                        let query = Query::Bool {
                            clauses: BoolQuery {
                                must: if required {
                                    vec![Query::MatchAll]
                                } else {
                                    vec![]
                                },
                                should: ["a", "b", "c", "a"]
                                    .iter()
                                    .take(count)
                                    .map(|field| term(field))
                                    .collect(),
                                filter: if filtered {
                                    vec![term("allowed")]
                                } else {
                                    vec![]
                                },
                                must_not: if excluded { vec![term("c")] } else { vec![] },
                                minimum_should_match: Some(1),
                            },
                        };
                        let source = index
                            .refreshed_documents_for_shards(None)
                            .into_iter()
                            .filter_map(|document| {
                                index
                                    .score_document_query(&query, document)
                                    .unwrap()
                                    .map(|score| (document.metadata.id.clone(), score))
                            })
                            .collect::<BTreeMap<_, _>>();
                        assert_eq!(native_scores(index,&query,false),source,
                            "shards={shards} count={count} required={required} filtered={filtered} excluded={excluded}");
                    }
                }
            }
        }
    }
}
