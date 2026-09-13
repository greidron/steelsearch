use super::*;

fn native_deferred_replay_node(name: &str) -> SteelNode {
    SteelNode::new(NodeInfo {
        name: name.to_string(),
        version: OPENSEARCH_3_7_0_TRANSPORT,
    })
}

fn captured_document(node: &SteelNode, key: &str) -> SharedStoredDocument {
    Arc::clone(
        node.documents_state
            .lock()
            .unwrap()
            .get(key)
            .unwrap_or_else(|| panic!("missing runtime document for key [{key}]")),
    )
}

fn native_document(
    node: &SteelNode,
    index: &str,
    id: &str,
) -> Option<os_engine::GetDocumentResponse> {
    node.native_engine
        .get_document(os_engine::GetDocumentRequest {
            index: index.to_string(),
            id: id.to_string(),
        })
        .unwrap()
}

#[test]
fn replay_pending_native_index_replays_the_current_document() {
    let index = "native-deferred-current";
    let id = "one";
    let key = "native-deferred-current:one:";
    let node = native_deferred_replay_node(index);
    assert_eq!(
        node.handle_rest_request(RestRequest::new(RestMethod::Put, format!("/{index}")))
            .status,
        200
    );
    assert_eq!(
        node.handle_rest_request(
            RestRequest::new(RestMethod::Put, format!("/{index}/_doc/{id}"))
                .with_json_body(serde_json::json!({"value": "current"})),
        )
        .status,
        201
    );
    let captured = captured_document(&node, key);

    node.native_engine
        .delete_document_with_routing(
            os_engine::DeleteDocumentRequest {
                index: index.to_string(),
                id: id.to_string(),
            },
            None,
        )
        .unwrap();
    assert!(native_document(&node, index, id).is_none());

    node.replay_pending_native_index(index, key, id, &captured)
        .unwrap();

    assert_eq!(
        native_document(&node, index, id).unwrap().source,
        serde_json::json!({"value": "current"})
    );
}

#[test]
fn replay_pending_native_index_skips_a_replaced_document_snapshot() {
    let index = "native-deferred-replaced";
    let id = "one";
    let key = "native-deferred-replaced:one:";
    let node = native_deferred_replay_node(index);
    assert_eq!(
        node.handle_rest_request(RestRequest::new(RestMethod::Put, format!("/{index}")))
            .status,
        200
    );
    assert_eq!(
        node.handle_rest_request(
            RestRequest::new(RestMethod::Put, format!("/{index}/_doc/{id}"))
                .with_json_body(serde_json::json!({"value": "old"})),
        )
        .status,
        201
    );
    let captured = captured_document(&node, key);
    assert_eq!(
        node.handle_rest_request(
            RestRequest::new(RestMethod::Put, format!("/{index}/_doc/{id}"))
                .with_json_body(serde_json::json!({"value": "replacement"})),
        )
        .status,
        200
    );
    let current = captured_document(&node, key);
    assert!(!Arc::ptr_eq(&captured, &current));

    node.replay_pending_native_index(index, key, id, &captured)
        .unwrap();

    assert_eq!(
        native_document(&node, index, id).unwrap().source,
        serde_json::json!({"value": "replacement"})
    );
}

#[test]
fn replay_pending_native_index_does_not_resurrect_a_removed_snapshot() {
    let index = "native-deferred-removed";
    let id = "one";
    let key = "native-deferred-removed:one:";
    let node = native_deferred_replay_node(index);
    assert_eq!(
        node.handle_rest_request(RestRequest::new(RestMethod::Put, format!("/{index}")))
            .status,
        200
    );
    assert_eq!(
        node.handle_rest_request(
            RestRequest::new(RestMethod::Put, format!("/{index}/_doc/{id}"))
                .with_json_body(serde_json::json!({"value": "removed"})),
        )
        .status,
        201
    );
    let captured = captured_document(&node, key);
    assert_eq!(
        node.handle_rest_request(RestRequest::new(
            RestMethod::Delete,
            format!("/{index}/_doc/{id}?refresh=true")
        ),)
            .status,
        200
    );
    assert!(node.documents_state.lock().unwrap().get(key).is_none());
    assert!(native_document(&node, index, id).is_none());

    node.replay_pending_native_index(index, key, id, &captured)
        .unwrap();

    assert!(native_document(&node, index, id).is_none());
}

#[test]
fn replay_pending_native_index_propagates_a_missing_native_index() {
    let index = "native-deferred-missing";
    let id = "one";
    let key = "native-deferred-missing:one:";
    let node = native_deferred_replay_node(index);
    assert_eq!(
        node.handle_rest_request(RestRequest::new(RestMethod::Put, format!("/{index}")))
            .status,
        200
    );
    assert_eq!(
        node.handle_rest_request(
            RestRequest::new(RestMethod::Put, format!("/{index}/_doc/{id}"))
                .with_json_body(serde_json::json!({"value": "current"})),
        )
        .status,
        201
    );
    let captured = captured_document(&node, key);
    node.native_engine.delete_index(index).unwrap();
    assert!(matches!(
        node.native_engine
            .get_document(os_engine::GetDocumentRequest {
                index: index.to_string(),
                id: id.to_string(),
            }),
        Err(os_engine::EngineError::IndexNotFound { .. })
    ));

    let error = node
        .replay_pending_native_index(index, key, id, &captured)
        .unwrap_err();

    assert!(matches!(
        error,
        os_engine::EngineError::IndexNotFound { .. }
    ));
}

#[test]
fn replay_pending_native_index_rejects_negative_metadata_on_the_current_snapshot() {
    for field in ["version", "primary_term"] {
        let index = format!("native-deferred-invalid-{field}");
        let id = "one";
        let key = format!("{index}:{id}:");
        let node = native_deferred_replay_node(&index);
        assert_eq!(
            node.handle_rest_request(RestRequest::new(RestMethod::Put, format!("/{index}")),)
                .status,
            200
        );
        assert_eq!(
            node.handle_rest_request(
                RestRequest::new(RestMethod::Put, format!("/{index}/_doc/{id}"))
                    .with_json_body(serde_json::json!({"value": "current"})),
            )
            .status,
            201
        );
        let current = captured_document(&node, &key);
        let mut invalid = (*current).clone();
        if field == "version" {
            invalid.version = -1;
        } else {
            invalid.primary_term = -1;
        }
        let invalid = Arc::new(invalid);
        node.documents_state
            .lock()
            .unwrap()
            .insert(key.clone(), Arc::clone(&invalid));

        let error = node
            .replay_pending_native_index(&index, &key, id, &invalid)
            .unwrap_err();

        assert!(
            matches!(error, os_engine::EngineError::InvalidRequest { .. }),
            "{field}"
        );
        assert_eq!(
            native_document(&node, &index, id).unwrap().source,
            serde_json::json!({"value": "current"}),
            "{field}"
        );
    }
}
