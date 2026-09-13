use super::*;
use os_engine::{DocumentMetadata, SearchHit};
use std::panic::{catch_unwind, AssertUnwindSafe};

fn native_response_mapping_test_node() -> SteelNode {
    SteelNode::new(NodeInfo {
        name: "native-response-mapping-test".to_string(),
        version: OPENSEARCH_3_7_0_TRANSPORT,
    })
}

fn poison_metadata_mutex(node: &SteelNode) {
    let metadata = Arc::clone(&node.metadata_manifest_state);
    let _ = catch_unwind(AssertUnwindSafe(|| {
        let _guard = metadata
            .lock()
            .expect("test metadata mutex starts unlocked");
        panic!("poison metadata mutex for bounded mapping-access proof");
    }));
}

#[test]
fn native_response_mapping_skips_metadata_for_absent_null_empty_and_invalid_sorts() {
    let node = native_response_mapping_test_node();
    poison_metadata_mutex(&node);
    let resolved_indices = vec!["logs".to_string()];

    for body in [
        serde_json::json!({}),
        serde_json::json!({"sort": null}),
        serde_json::json!({"sort": []}),
        serde_json::json!({"sort": {}}),
        serde_json::json!({"sort": false}),
        serde_json::json!({"sort": [null]}),
    ] {
        assert!(node
            .index_mappings_for_native_response(&resolved_indices, &body)
            .is_none());
    }
}

#[test]
fn native_response_mapping_keeps_mappings_for_date_date_nanos_and_numeric_sorts() {
    let node = native_response_mapping_test_node();
    let resolved_indices = vec!["logs".to_string()];
    node.metadata_manifest_state.lock().unwrap()["indices"]["logs"] = serde_json::json!({
        "mappings": {"properties": {
            "timestamp": {"type": "date"},
            "timestamp_nanos": {"type": "date_nanos"},
            "rank": {"type": "long"}
        }}
    });

    for (field, value, expected) in [
        (
            "timestamp",
            serde_json::json!("1970-01-01T00:00:01Z"),
            serde_json::json!(1000),
        ),
        (
            "timestamp_nanos",
            serde_json::json!("1970-01-01T00:00:01Z"),
            serde_json::json!(1000),
        ),
        ("rank", serde_json::json!(7), serde_json::json!(7)),
    ] {
        let body = serde_json::json!({"sort": [field]});
        let mappings = node
            .index_mappings_for_native_response(&resolved_indices, &body)
            .expect("explicit sort retains index mappings");
        assert!(mappings.contains_key("logs"));

        let rest_response = native_search_response_to_rest_response(
            SearchResponse::new(
                1,
                vec![SearchHit {
                    index: "logs".to_string(),
                    metadata: DocumentMetadata {
                        id: "1".to_string(),
                        version: 1,
                        seq_no: 0,
                        primary_term: 1,
                    },
                    score: 1.0,
                    source: serde_json::json!({}),
                    sort: Some(Value::Array(vec![value])),
                    fields: None,
                    highlight: None,
                    explanation: None,
                    inner_hits: None,
                }],
                serde_json::json!({}),
            ),
            &body,
            1,
            false,
            false,
            Some(&mappings),
        );
        assert_eq!(rest_response.body["hits"]["hits"][0]["sort"][0], expected);
    }
}

#[test]
fn native_response_without_sort_matches_the_original_mapping_aware_response() {
    let response = SearchResponse::new(
        1,
        vec![SearchHit {
            index: "logs".to_string(),
            metadata: DocumentMetadata {
                id: "1".to_string(),
                version: 2,
                seq_no: 3,
                primary_term: 4,
            },
            score: 1.0,
            source: serde_json::json!({"timestamp": "1970-01-01T00:00:01Z"}),
            sort: Some(serde_json::json!(["1970-01-01T00:00:01Z"])),
            fields: None,
            highlight: None,
            explanation: None,
            inner_hits: None,
        }],
        serde_json::json!({"total_rank": {"value": 7}}),
    );
    let body = serde_json::json!({"aggs": {"total_rank": {"sum": {"field": "rank"}}}});
    let mappings = std::collections::HashMap::from([(
        "logs".to_string(),
        serde_json::json!({"properties": {"timestamp": {"type": "date"}}}),
    )]);

    let original = native_search_response_to_rest_response(
        response.clone(),
        &body,
        1,
        false,
        false,
        Some(&mappings),
    );
    let optimized = native_search_response_to_rest_response(response, &body, 1, false, false, None);

    assert_eq!(optimized.body, original.body);
    assert_eq!(
        optimized.body["hits"]["hits"][0]["sort"],
        serde_json::json!(["1970-01-01T00:00:01Z"])
    );
    assert_eq!(
        optimized.body["aggregations"],
        serde_json::json!({"total_rank": {"value": 7}})
    );
}
