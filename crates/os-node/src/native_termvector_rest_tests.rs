use super::*;

#[test]
fn realtime_termvectors_replay_pending_routed_writes_without_publishing_search() {
    let node = SteelNode::new(NodeInfo {
        name: "pending-tv".into(),
        version: OPENSEARCH_3_7_0_TRANSPORT,
    });
    assert_eq!(node.handle_rest_request(RestRequest::new(RestMethod::Put, "/pending-tv")
        .with_json_body(serde_json::json!({"settings":{"number_of_shards":3},
            "mappings":{"properties":{"body":{"type":"text","term_vector":"with_positions_offsets"}}}}))).status, 200);
    let vectors = |realtime: bool| {
        node.handle_rest_request(
            RestRequest::new(
                RestMethod::Post,
                format!("/pending-tv/_termvectors/a?routing=tenant&realtime={realtime}"),
            )
            .with_json_body(serde_json::json!({"fields":["body"],"field_statistics":false})),
        )
    };
    for (ordinal, word) in ["first", "second"].iter().enumerate() {
        let write = node.handle_rest_request(
            RestRequest::new(
                RestMethod::Put,
                "/pending-tv/_doc/a?routing=tenant&refresh=false",
            )
            .with_json_body(serde_json::json!({"body":word})),
        );
        assert_eq!(write.status, if ordinal == 0 { 201 } else { 200 });
        if ordinal == 0
            && std::env::var("STEELSEARCH_DEFER_NATIVE_WRITE_UNTIL_REFRESH").as_deref() == Ok("1")
        {
            assert!(node
                .native_engine
                .get_document(os_engine::GetDocumentRequest {
                    index: "pending-tv".into(),
                    id: "a".into(),
                })
                .unwrap()
                .is_none());
        }
        assert_eq!(vectors(false).body["found"], false);
        let current = vectors(true);
        assert_eq!(current.status, 200, "{}", current.body);
        assert_eq!(current.body["found"], true);
        assert_eq!(current.body["_version"], ordinal + 1);
        let terms = current.body["term_vectors"]["body"]["terms"]
            .as_object()
            .unwrap();
        assert_eq!(terms.len(), 1);
        assert_eq!(terms[*word]["term_freq"], 1);
        let multi = node.handle_rest_request(
            RestRequest::new(RestMethod::Post, "/pending-tv/_mtermvectors?realtime=true")
                .with_json_body(
                    serde_json::json!({"docs":[{"_id":"a","routing":"tenant","fields":["body"]}]}),
                ),
        );
        assert_eq!(multi.status, 200, "{}", multi.body);
        assert_eq!(multi.body["docs"][0]["found"], true);
        assert_eq!(multi.body["docs"][0]["_version"], ordinal + 1);
        assert_eq!(
            multi.body["docs"][0]["term_vectors"]["body"]["terms"],
            Value::Object(terms.clone())
        );
        assert_eq!(vectors(false).body["found"], false);
        let search = node.handle_rest_request(
            RestRequest::new(RestMethod::Post, "/pending-tv/_search")
                .with_json_body(serde_json::json!({"query":{"match_all":{}}})),
        );
        assert_eq!(search.status, 200, "{}", search.body);
        assert_eq!(search.body["hits"]["total"]["value"], 0);
    }
    assert_eq!(
        node.handle_rest_request(RestRequest::new(
            RestMethod::Delete,
            "/pending-tv/_doc/a?routing=tenant&refresh=false"
        ))
        .status,
        200
    );
    assert_eq!(vectors(true).body["found"], false);
    assert_eq!(vectors(false).body["found"], false);
    assert_eq!(
        node.handle_rest_request(RestRequest::new(RestMethod::Post, "/pending-tv/_refresh"))
            .status,
        200
    );
    assert_eq!(vectors(false).body["found"], false);
}

#[test]
fn generated_termvectors_require_selected_fields_and_expand_wildcards() {
    let node = SteelNode::new(NodeInfo {
        name: "native-generated-termvector-rest".into(),
        version: OPENSEARCH_3_7_0_TRANSPORT,
    });
    assert_eq!(
        node.handle_rest_request(
            RestRequest::new(RestMethod::Put, "/native-generated-tv").with_json_body(
                serde_json::json!({"mappings":{"properties":{
                    "body":{"type":"text"}, "other":{"type":"text"}, "tag":{"type":"keyword"}
                }}})
            )
        )
        .status,
        200
    );
    assert_eq!(node.handle_rest_request(RestRequest::new(RestMethod::Put,
        "/native-generated-tv/_doc/a?refresh=true")
        .with_json_body(serde_json::json!({"body":"alpha beta", "other":"hidden", "tag":["tag value","tag value"]}))).status, 201);
    let omitted = node.handle_rest_request(RestRequest::new(
        RestMethod::Post,
        "/native-generated-tv/_termvectors/a?realtime=false",
    ));
    assert_eq!(omitted.status, 200);
    assert_eq!(omitted.body["found"], true);
    assert_eq!(omitted.body["term_vectors"], serde_json::json!({}));
    let keyword = node.handle_rest_request(
        RestRequest::new(
            RestMethod::Post,
            "/native-generated-tv/_termvectors/a?realtime=false",
        )
        .with_json_body(serde_json::json!({"fields":["tag"], "field_statistics":false})),
    );
    assert_eq!(keyword.status, 200, "{}", keyword.body);
    assert_eq!(
        keyword.body["term_vectors"],
        serde_json::json!({"tag":{"terms":{
            "tag value":{"term_freq":2,"tokens":[
                {"position":0,"start_offset":0,"end_offset":9},
                {"position":1,"start_offset":10,"end_offset":19}
            ]}
        }}})
    );
    let selected = node.handle_rest_request(
        RestRequest::new(
            RestMethod::Post,
            "/native-generated-tv/_termvectors/a?realtime=false",
        )
        .with_json_body(serde_json::json!({"fields":["bo*", "missing*"]})),
    );
    assert_eq!(selected.status, 200, "{}", selected.body);
    assert_eq!(
        selected.body["term_vectors"],
        serde_json::json!({"body":{
            "field_statistics":{"doc_count":1,"sum_doc_freq":2,"sum_ttf":2},
            "terms":{
                "alpha":{"term_freq":1,"tokens":[{"position":0,"start_offset":0,"end_offset":5}]},
                "beta":{"term_freq":1,"tokens":[{"position":1,"start_offset":6,"end_offset":10}]}
            }
        }})
    );
    let multi = node.handle_rest_request(
        RestRequest::new(
            RestMethod::Post,
            "/native-generated-tv/_mtermvectors?realtime=false",
        )
        .with_json_body(serde_json::json!({"docs":[
            {"_id":"a","fields":["bo*"]}, {"_id":"a"},
            {"_id":"a","fields":[]}, {"_id":"a","fields":["bod?"]}
        ]})),
    );
    assert_eq!(multi.status, 200, "{}", multi.body);
    assert_eq!(
        multi.body["docs"][0]["term_vectors"],
        selected.body["term_vectors"]
    );
    for ordinal in [1, 2, 3] {
        assert_eq!(multi.body["docs"][ordinal]["found"], true);
        assert_eq!(
            multi.body["docs"][ordinal]["term_vectors"],
            serde_json::json!({})
        );
    }
}

#[test]
fn per_field_analyzer_regenerates_native_termvectors_for_stored_generated_and_multi_docs() {
    let node = SteelNode::new(NodeInfo {
        name: "native-termvector-analyzer-rest".into(),
        version: OPENSEARCH_3_7_0_TRANSPORT,
    });
    let expected_keyword = serde_json::json!({"terms": {
        "first two": {"term_freq": 1, "tokens": [
            {"position": 0, "start_offset": 0, "end_offset": 9}
        ]},
        "second three": {"term_freq": 1, "tokens": [
            {"position": 101, "start_offset": 10, "end_offset": 22}
        ]}
    }});
    for (index, stored) in [
        ("native-tv-analyzer-stored", true),
        ("native-tv-analyzer-generated", false),
    ] {
        let body_mapping = if stored {
            serde_json::json!({"type":"text","term_vector":"with_positions_offsets"})
        } else {
            serde_json::json!({"type":"text"})
        };
        assert_eq!(
            node.handle_rest_request(
                RestRequest::new(RestMethod::Put, format!("/{index}")).with_json_body(
                    serde_json::json!({"mappings":{"properties":{"body":body_mapping}}})
                )
            )
            .status,
            200
        );
        assert_eq!(
            node.handle_rest_request(
                RestRequest::new(RestMethod::Put, format!("/{index}/_doc/a?refresh=true"))
                    .with_json_body(serde_json::json!({"body":["first two", "second three"]}))
            )
            .status,
            201
        );
        let keyword = node.handle_rest_request(
            RestRequest::new(RestMethod::Post, format!("/{index}/_termvectors/a")).with_json_body(
                serde_json::json!({"fields":["body"],"field_statistics":false,
                "per_field_analyzer":{"body":"keyword"}}),
            ),
        );
        assert_eq!(keyword.status, 200, "{}", keyword.body);
        assert_eq!(
            keyword.body["term_vectors"]["body"], expected_keyword,
            "{index}"
        );

        let default = node.handle_rest_request(
            RestRequest::new(RestMethod::Post, format!("/{index}/_termvectors/a"))
                .with_json_body(serde_json::json!({"fields":["body"],"field_statistics":false})),
        );
        let unknown = node.handle_rest_request(
            RestRequest::new(RestMethod::Post, format!("/{index}/_termvectors/a")).with_json_body(
                serde_json::json!({"fields":["body"],"field_statistics":false,
                "perFieldAnalyzer":{"body":"absent-analyzer"}}),
            ),
        );
        assert_eq!(unknown.status, 200, "{}", unknown.body);
        assert_eq!(
            unknown.body["term_vectors"], default.body["term_vectors"],
            "{index}"
        );

        let multi = node.handle_rest_request(
            RestRequest::new(RestMethod::Post, format!("/{index}/_mtermvectors"))
                .with_json_body(serde_json::json!({"docs":[{"_id":"a","fields":["body"],
                "field_statistics":false,"per_field_analyzer":{"body":"keyword"}}]})),
        );
        assert_eq!(multi.status, 200, "{}", multi.body);
        assert_eq!(
            multi.body["docs"][0]["term_vectors"]["body"], expected_keyword,
            "{index}"
        );
    }
}

#[test]
fn per_field_analyzer_rejects_non_object_and_non_string_values() {
    let node = SteelNode::new(NodeInfo {
        name: "native-termvector-analyzer-errors".into(),
        version: OPENSEARCH_3_7_0_TRANSPORT,
    });
    assert_eq!(
        node.handle_rest_request(
            RestRequest::new(RestMethod::Put, "/native-tv-analyzer-errors").with_json_body(
                serde_json::json!({"mappings":{"properties":{"body":{"type":"text"}}}})
            )
        )
        .status,
        200
    );
    for value in [
        serde_json::json!("keyword"),
        serde_json::json!({"body": false}),
    ] {
        let response = node.handle_rest_request(
            RestRequest::new(
                RestMethod::Post,
                "/native-tv-analyzer-errors/_termvectors/a",
            )
            .with_json_body(serde_json::json!({"per_field_analyzer":value})),
        );
        assert_eq!(response.status, 400, "{}", response.body);
        assert_eq!(response.body["error"]["type"], "parse_exception");
    }
}

#[test]
fn published_termvectors_use_native_terms_flags_and_snapshot_visibility() {
    let node = SteelNode::new(NodeInfo {
        name: "native-termvector-rest".into(),
        version: OPENSEARCH_3_7_0_TRANSPORT,
    });
    assert_eq!(
        node.handle_rest_request(
            RestRequest::new(RestMethod::Put, "/native-tv-rest").with_json_body(
                serde_json::json!({"mappings":{"properties":{
                    "body":{"type":"text","term_vector":"with_positions_offsets"}
                }}})
            )
        )
        .status,
        200
    );
    assert_eq!(
        node.handle_rest_request(
            RestRequest::new(RestMethod::Put, "/native-tv-rest/_doc/a")
                .with_json_body(serde_json::json!({"body":["alpha", "beta beta"]}))
        )
        .status,
        201
    );
    let missing = node.handle_rest_request(RestRequest::new(
        RestMethod::Post,
        "/native-tv-rest/_termvectors/a?realtime=false",
    ));
    assert_eq!(missing.status, 200);
    assert_eq!(missing.body["found"], false);
    let pending = node.handle_rest_request(RestRequest::new(
        RestMethod::Post,
        "/native-tv-rest/_termvectors/a?positions=false&offsets=false&field_statistics=false",
    ));
    assert_eq!(pending.status, 200, "{}", pending.body);
    assert_eq!(pending.body["found"], true);
    assert_eq!(
        pending.body["term_vectors"]["body"],
        serde_json::json!({"terms":{
            "alpha":{"term_freq":1},"beta":{"term_freq":2}
        }})
    );
    let search = node.handle_rest_request(
        RestRequest::new(RestMethod::Post, "/native-tv-rest/_search")
            .with_json_body(serde_json::json!({"query":{"match_all":{}}})),
    );
    assert_eq!(search.status, 200, "{}", search.body);
    assert_eq!(search.body["hits"]["total"]["value"], 0);
    assert_eq!(
        node.handle_rest_request(RestRequest::new(
            RestMethod::Post,
            "/native-tv-rest/_refresh"
        ))
        .status,
        200
    );
    let response = node.handle_rest_request(
        RestRequest::new(
            RestMethod::Post,
            "/native-tv-rest/_termvectors/a?realtime=false",
        )
        .with_json_body(serde_json::json!({
            "fields":["body"], "term_statistics":true
        })),
    );
    assert_eq!(response.status, 200, "{}", response.body);
    assert_eq!(
        response.body["term_vectors"]["body"],
        serde_json::json!({
            "field_statistics":{"doc_count":1,"sum_doc_freq":2,"sum_ttf":3},
            "terms":{
                "alpha":{"term_freq":1,"doc_freq":1,"ttf":1,"tokens":[
                    {"position":0,"start_offset":0,"end_offset":5}]},
                "beta":{"term_freq":2,"doc_freq":1,"ttf":2,"tokens":[
                    {"position":101,"start_offset":6,"end_offset":10},
                    {"position":102,"start_offset":11,"end_offset":15}]}
            }
        })
    );
    assert_eq!(
        node.handle_rest_request(
            RestRequest::new(RestMethod::Put, "/native-tv-rest/_doc/a")
                .with_json_body(serde_json::json!({"body":"pending"}))
        )
        .status,
        200
    );
    let flags = node.handle_rest_request(RestRequest::new(RestMethod::Post,
        "/native-tv-rest/_termvectors/a?realtime=false&positions=false&offsets=false&field_statistics=false&term_statistics=false")
        .with_json_body(serde_json::json!({"fields":["body"], "positions":true})));
    assert_eq!(flags.status, 200, "{}", flags.body);
    assert_eq!(
        flags.body["term_vectors"]["body"],
        serde_json::json!({"terms":{
            "alpha":{"term_freq":1},"beta":{"term_freq":2}
        }})
    );
}
