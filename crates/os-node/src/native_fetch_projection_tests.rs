use super::*;

fn native_fetch_projection_test_node() -> SteelNode {
    SteelNode::new(NodeInfo {
        name: "native-fetch-projection-test".to_string(),
        version: OPENSEARCH_3_7_0_TRANSPORT,
    })
}

fn native_fetch_projection_response() -> Value {
    serde_json::json!({
        "hits": {
            "hits": [{
                "_index": "logs",
                "_id": "1",
                "_source": {
                    "count": [7, 11],
                    "stored": "stored-value",
                    "visible": "public-value",
                    "hidden": "private-value"
                }
            }]
        }
    })
}

fn install_native_fetch_projection_mappings(node: &SteelNode) {
    node.metadata_manifest_state.lock().unwrap()["indices"]["logs"] = serde_json::json!({
        "mappings": {
            "properties": {
                "count": {"type": "long"},
                "stored": {"type": "keyword", "store": true},
                "visible": {"type": "keyword"},
                "hidden": {"type": "keyword"}
            }
        }
    });
}

#[test]
fn native_request_preserves_ordinary_source_projection_and_defers_it_for_fetches() {
    let indices = vec!["logs".to_string()];
    let alias_filters = BTreeMap::from([(
        "logs".to_string(),
        serde_json::json!({"term": {"tenant": "tenant-a"}}),
    )]);
    let ordinary = serde_json::json!({
        "_source": {"includes": ["visible"], "excludes": ["hidden"]},
        "_source_includes": ["visible"],
        "_source_include": "visible",
        "_source_excludes": ["hidden"],
        "_source_exclude": "hidden"
    });

    let request = standalone_native_search_request_with_alias_filters(
        &indices,
        None,
        &alias_filters,
        &ordinary,
    )
    .expect("ordinary native request should parse");
    assert_eq!(request.source_filter, Some(ordinary["_source"].clone()));
    assert_eq!(
        request.source_includes,
        Some(ordinary["_source_includes"].clone())
    );
    assert_eq!(
        request.source_include,
        Some(ordinary["_source_include"].clone())
    );
    assert_eq!(
        request.source_excludes,
        Some(ordinary["_source_excludes"].clone())
    );
    assert_eq!(
        request.source_exclude,
        Some(ordinary["_source_exclude"].clone())
    );

    for body in [
        serde_json::json!({"_source": false, "fields": ["visible"]}),
        serde_json::json!({
            "_source": {"fetch": false},
            "docvalue_fields": ["count"]
        }),
        serde_json::json!({
            "_source": {"includes": ["visible"], "excludes": ["hidden"]},
            "_source_includes": ["visible"],
            "_source_include": "visible",
            "_source_excludes": ["hidden"],
            "_source_exclude": "hidden",
            "stored_fields": ["stored"]
        }),
    ] {
        let request = standalone_native_search_request_with_alias_filters(
            &indices,
            None,
            &alias_filters,
            &body,
        )
        .expect("fetch request should parse");
        assert_eq!(request.source_filter, None, "{body}");
        assert_eq!(request.source_includes, None, "{body}");
        assert_eq!(request.source_include, None, "{body}");
        assert_eq!(request.source_excludes, None, "{body}");
        assert_eq!(request.source_exclude, None, "{body}");
    }
}

#[test]
fn native_final_page_extracts_full_source_before_projecting_public_source() {
    let node = native_fetch_projection_test_node();
    install_native_fetch_projection_mappings(&node);
    let body = serde_json::json!({
        "_source": {"includes": ["visible"], "excludes": ["hidden"]},
        "docvalue_fields": ["count"],
        "stored_fields": ["stored"],
        "fields": ["hidden", "visible"]
    });
    let mut response = native_fetch_projection_response();

    node.apply_native_search_fetch_fields(&mut response, &body);
    apply_native_search_source_visibility(&mut response, &body);

    let hit = &response["hits"]["hits"][0];
    assert_eq!(hit["fields"]["count"], serde_json::json!([7, 11]));
    assert_eq!(hit["fields"]["stored"], serde_json::json!(["stored-value"]));
    assert_eq!(
        hit["fields"]["hidden"],
        serde_json::json!(["private-value"])
    );
    assert_eq!(
        hit["fields"]["visible"],
        serde_json::json!(["public-value"])
    );
    assert_eq!(
        hit["_source"],
        serde_json::json!({"visible": "public-value"})
    );
    assert!(hit["_source"].get("hidden").is_none());
    assert!(hit["_source"].get("count").is_none());
    assert!(hit["_source"].get("stored").is_none());
}

#[test]
fn native_fetch_visibility_hides_source_for_boolean_and_object_false() {
    let node = native_fetch_projection_test_node();
    install_native_fetch_projection_mappings(&node);
    for source in [
        serde_json::json!(false),
        serde_json::json!({"fetch": false}),
    ] {
        let body = serde_json::json!({"_source": source, "docvalue_fields": ["count"]});
        let mut response = native_fetch_projection_response();
        node.apply_native_search_fetch_fields(&mut response, &body);
        apply_native_search_source_visibility(&mut response, &body);
        let hit = &response["hits"]["hits"][0];
        assert_eq!(hit["fields"]["count"], serde_json::json!([7, 11]));
        assert!(hit.get("_source").is_none(), "{body}");
    }
}

#[test]
fn native_stored_fields_hide_default_source_but_honor_explicit_source_requests() {
    let node = native_fetch_projection_test_node();
    install_native_fetch_projection_mappings(&node);
    for fields in [serde_json::json!(["stored"]), serde_json::json!("stored")] {
        let body = serde_json::json!({"stored_fields": fields});
        let mut response = native_fetch_projection_response();
        node.apply_native_search_fetch_fields(&mut response, &body);
        apply_native_search_source_visibility(&mut response, &body);
        let hit = &response["hits"]["hits"][0];
        assert_eq!(hit["fields"]["stored"], serde_json::json!(["stored-value"]));
        assert!(hit.get("_source").is_none(), "{body}");
    }
    for body in [
        serde_json::json!({"stored_fields": ["stored"], "_source": true}),
        serde_json::json!({"stored_fields": ["stored", "_source"]}),
        serde_json::json!({"stored_fields": ["stored", "_source"], "_source": false}),
    ] {
        let mut response = native_fetch_projection_response();
        node.apply_native_search_fetch_fields(&mut response, &body);
        apply_native_search_source_visibility(&mut response, &body);
        let hit = &response["hits"]["hits"][0];
        assert_eq!(hit["fields"]["stored"], serde_json::json!(["stored-value"]));
        assert_eq!(
            hit["_source"],
            native_fetch_projection_response()["hits"]["hits"][0]["_source"],
            "{body}"
        );
    }
}

#[test]
fn native_fetch_projection_handles_null_or_empty_fields_and_suppresses_empty_stored_source() {
    let node = native_fetch_projection_test_node();
    install_native_fetch_projection_mappings(&node);

    for body in [
        serde_json::json!({"fields": null}),
        serde_json::json!({"fields": []}),
        serde_json::json!({"docvalue_fields": []}),
    ] {
        let request = standalone_native_search_request(&["logs".to_string()], None, &body)
            .expect("null or empty fetch selectors should parse");
        assert_eq!(request.source_filter, None, "{body}");
        let mut response = native_fetch_projection_response();
        node.apply_native_search_fetch_fields(&mut response, &body);
        apply_native_search_source_visibility(&mut response, &body);
        assert!(response["hits"]["hits"][0].get("_source").is_some());
    }

    let body = serde_json::json!({
        "stored_fields": [],
        "docvalue_fields": ["count"]
    });
    let mut response = native_fetch_projection_response();
    node.apply_native_search_fetch_fields(&mut response, &body);
    apply_native_search_source_visibility(&mut response, &body);
    let hit = &response["hits"]["hits"][0];
    assert_eq!(hit["fields"]["count"], serde_json::json!([7, 11]));
    assert!(hit.get("_source").is_none());
}

#[test]
fn rest_native_search_fetches_unprojected_values_without_leaking_source() {
    let node = native_fetch_projection_test_node();
    let index = "logs-native-fetch-projection-000001";
    assert_eq!(
        node.handle_rest_request(
            RestRequest::new(RestMethod::Put, format!("/{index}")).with_json_body(
                serde_json::json!({
                    "mappings": {"properties": {
                        "count": {"type": "long"},
                        "stored": {"type": "keyword", "store": true},
                        "visible": {"type": "keyword"},
                        "hidden": {"type": "keyword"}
                    }}
                }),
            ),
        )
        .status,
        200
    );
    assert_eq!(
        node.handle_rest_request(
            RestRequest::new(RestMethod::Put, format!("/{index}/_doc/1")).with_json_body(
                serde_json::json!({
                    "count": [7, 11],
                    "stored": "stored-value",
                    "visible": "public-value",
                    "hidden": "private-value"
                }),
            ),
        )
        .status,
        201
    );
    assert_eq!(
        node.handle_rest_request(RestRequest::new(
            RestMethod::Post,
            format!("/{index}/_refresh")
        ))
        .status,
        200
    );

    let indices = vec![index.to_string()];
    let hidden = serde_json::json!({"_source": false, "docvalue_fields": ["count"]});
    let ordinary = node
        .try_native_engine_search_response(
            &indices,
            &BTreeMap::new(),
            &BTreeMap::new(),
            &hidden,
            false,
            false,
        )
        .expect("exercise native ordinary search, not fallback");
    let scroll = node
        .try_native_engine_scroll_search_response(
            &indices,
            &BTreeMap::new(),
            &hidden,
            Some("1m"),
            false,
            false,
        )
        .expect("exercise native scroll, not fallback");
    let opened = node.handle_rest_request(RestRequest::new(
        RestMethod::Post,
        format!("/{index}/_search/point_in_time?keep_alive=1m"),
    ));
    assert_eq!(opened.status, 200, "{}", opened.body);
    let pit_id = opened.body["pit_id"].as_str().unwrap();
    let context = node.resolve_pit_context(pit_id, None).unwrap();
    let stored_only = serde_json::json!({"stored_fields": ["stored"]});
    let stored_responses = [
        node.try_native_engine_search_response(
            &indices,
            &BTreeMap::new(),
            &BTreeMap::new(),
            &stored_only,
            false,
            false,
        )
        .unwrap(),
        node.try_native_engine_scroll_search_response(
            &indices,
            &BTreeMap::new(),
            &stored_only,
            Some("1m"),
            false,
            false,
        )
        .unwrap(),
        node.try_native_engine_pit_search_response(
            &indices,
            &context,
            &stored_only,
            Some(pit_id),
            false,
            false,
        )
        .unwrap(),
    ];
    for response in stored_responses {
        assert_eq!(response.status, 200, "{}", response.body);
        let hit = &response.body["hits"]["hits"][0];
        assert_eq!(hit["fields"]["stored"], serde_json::json!(["stored-value"]));
        assert!(hit.get("_source").is_none());
    }
    let pit = node
        .try_native_engine_pit_search_response(
            &indices,
            &context,
            &hidden,
            Some(pit_id),
            false,
            false,
        )
        .expect("exercise native PIT, not fallback");
    for response in [ordinary, scroll, pit] {
        assert_eq!(response.status, 200, "{}", response.body);
        assert_eq!(response.body["hits"]["hits"].as_array().unwrap().len(), 1);
        let hit = &response.body["hits"]["hits"][0];
        assert_eq!(hit["fields"]["count"], serde_json::json!([7, 11]));
        assert!(hit.get("_source").is_none());
    }

    let response = node.handle_rest_request(
        RestRequest::new(RestMethod::Post, format!("/{index}/_search")).with_json_body(
            serde_json::json!({
                "query": {"match_all": {}},
                "_source": {"includes": ["visible"], "excludes": ["hidden"]},
                "docvalue_fields": ["count"],
                "stored_fields": ["stored"],
                "fields": ["hidden"]
            }),
        ),
    );

    assert_eq!(response.status, 200, "{}", response.body);
    let hit = &response.body["hits"]["hits"][0];
    assert_eq!(hit["fields"]["count"], serde_json::json!([7, 11]));
    assert_eq!(hit["fields"]["stored"], serde_json::json!(["stored-value"]));
    assert_eq!(
        hit["fields"]["hidden"],
        serde_json::json!(["private-value"])
    );
    assert_eq!(
        hit["_source"],
        serde_json::json!({"visible": "public-value"})
    );
    assert!(hit["_source"].get("hidden").is_none());
    assert!(hit["_source"].get("count").is_none());
    assert!(hit["_source"].get("stored").is_none());
}

#[test]
fn rest_native_fetch_projection_fixture_contracts_cover_search_pit_and_scroll() {
    let node = native_fetch_projection_test_node();
    let index = "native-fetch-projection-contract-000001";
    assert_eq!(
        node.handle_rest_request(
            RestRequest::new(RestMethod::Put, format!("/{index}")).with_json_body(
                serde_json::json!({
                    "mappings": {"properties": {
                        "rank": {"type": "long", "store": true},
                        "label": {"type": "keyword"}
                    }}
                }),
            ),
        )
        .status,
        200
    );
    for (id, source) in [
        ("a", serde_json::json!({"rank": 7, "label": "keep"})),
        (
            "b",
            serde_json::json!({"rank": [9, 2, 9], "label": "array"}),
        ),
    ] {
        assert_eq!(
            node.handle_rest_request(
                RestRequest::new(RestMethod::Put, format!("/{index}/_doc/{id}"))
                    .with_json_body(source),
            )
            .status,
            201,
            "{id}"
        );
    }
    assert_eq!(
        node.handle_rest_request(RestRequest::new(
            RestMethod::Post,
            format!("/{index}/_refresh")
        ))
        .status,
        200
    );

    let fetch_false = node.handle_rest_request(
        RestRequest::new(RestMethod::Post, format!("/{index}/_search"))
            .with_json_body(serde_json::json!({"size": 10, "_source": {"fetch": false}})),
    );
    assert_eq!(fetch_false.status, 400, "{}", fetch_false.body);
    assert_eq!(fetch_false.body["error"]["type"], "parsing_exception");
    assert_eq!(
        fetch_false.body["error"]["reason"],
        "Unknown key for a VALUE_BOOLEAN in [fetch]."
    );

    let body_excludes = node.handle_rest_request(
        RestRequest::new(RestMethod::Post, format!("/{index}/_search")).with_json_body(
            serde_json::json!({
                "size": 10,
                "_source_excludes": ["rank"],
                "docvalue_fields": ["rank"]
            }),
        ),
    );
    assert_eq!(body_excludes.status, 400, "{}", body_excludes.body);
    assert_eq!(body_excludes.body["error"]["type"], "parsing_exception");
    assert_eq!(
        body_excludes.body["error"]["reason"],
        "Unknown key for a START_ARRAY in [_source_excludes]."
    );

    let url_excludes = node.handle_rest_request(
        RestRequest::new(
            RestMethod::Post,
            format!("/{index}/_search?_source_excludes=rank"),
        )
        .with_json_body(serde_json::json!({"size": 10, "docvalue_fields": ["rank"]})),
    );
    assert_eq!(url_excludes.status, 200, "{}", url_excludes.body);
    let url_hits = url_excludes.body["hits"]["hits"].as_array().unwrap();
    assert_eq!(url_hits.len(), 2);
    for hit in url_hits {
        let expected_label = match hit["_id"].as_str() {
            Some("a") => "keep",
            Some("b") => "array",
            id => panic!("unexpected hit id {id:?}"),
        };
        assert_eq!(hit["_source"], serde_json::json!({"label": expected_label}));
        let ranks = if hit["_id"] == "a" {
            serde_json::json!([7])
        } else {
            serde_json::json!([2, 9, 9])
        };
        assert_eq!(hit["fields"]["rank"], ranks);
    }

    let opened = node.handle_rest_request(RestRequest::new(
        RestMethod::Post,
        format!("/{index}/_search/point_in_time?keep_alive=1m"),
    ));
    assert_eq!(opened.status, 200, "{}", opened.body);
    let pit_id = opened.body["pit_id"].as_str().unwrap().to_string();

    let empty_fields = serde_json::json!({"size": 10, "_source": false, "fields": []});
    let empty_fields_responses = [
        (
            "ordinary",
            node.handle_rest_request(
                RestRequest::new(RestMethod::Post, format!("/{index}/_search"))
                    .with_json_body(empty_fields.clone()),
            ),
        ),
        (
            "scroll",
            node.handle_rest_request(
                RestRequest::new(RestMethod::Post, format!("/{index}/_search?scroll=1m"))
                    .with_json_body(empty_fields.clone()),
            ),
        ),
        (
            "pit",
            node.handle_rest_request(
                RestRequest::new(RestMethod::Post, "/_search").with_json_body(serde_json::json!({
                    "size": 10,
                    "pit": {"id": pit_id.clone(), "keep_alive": "1m"},
                    "_source": false,
                    "fields": []
                })),
            ),
        ),
    ];
    for (kind, response) in empty_fields_responses {
        assert_eq!(response.status, 200, "{kind}: {}", response.body);
        let hits = response.body["hits"]["hits"].as_array().unwrap();
        assert_eq!(hits.len(), 2, "{kind}: {}", response.body);
        for hit in hits {
            assert!(hit.get("fields").is_none(), "{kind}: {hit}");
            assert!(hit.get("_source").is_none(), "{kind}: {hit}");
        }
    }

    let source_labels = serde_json::json!({"size": 10, "_source": ["label"]});
    let source_label_responses = [
        (
            "ordinary",
            node.handle_rest_request(
                RestRequest::new(RestMethod::Post, format!("/{index}/_search"))
                    .with_json_body(source_labels.clone()),
            ),
        ),
        (
            "scroll",
            node.handle_rest_request(
                RestRequest::new(RestMethod::Post, format!("/{index}/_search?scroll=1m"))
                    .with_json_body(source_labels.clone()),
            ),
        ),
        (
            "pit",
            node.handle_rest_request(
                RestRequest::new(RestMethod::Post, "/_search").with_json_body(serde_json::json!({
                    "size": 10,
                    "pit": {"id": pit_id.clone(), "keep_alive": "1m"},
                    "_source": ["label"]
                })),
            ),
        ),
    ];
    for (kind, response) in source_label_responses {
        assert_eq!(response.status, 200, "{kind}: {}", response.body);
        let hits = response.body["hits"]["hits"].as_array().unwrap();
        assert_eq!(hits.len(), 2, "{kind}: {}", response.body);
        for hit in hits {
            let expected_label = match hit["_id"].as_str() {
                Some("a") => "keep",
                Some("b") => "array",
                id => panic!("unexpected hit id {id:?}"),
            };
            assert_eq!(
                hit["_source"],
                serde_json::json!({"label": expected_label}),
                "{kind}: {hit}"
            );
            assert!(hit.get("fields").is_none(), "{kind}: {hit}");
        }
    }
}
