use super::*;
use tantivy::{DocSet, Postings};

#[test]
fn native_indexing_tokens_preserve_reference_termvector_offsets() {
    let fixture: Value = serde_json::from_str(include_str!(
        "../../../tools/fixtures/search-native-array-positions-compat.json"
    )).unwrap();
    let reference: Value = serde_json::from_str(include_str!(
        "../../../tools/fixtures/search-native-termvectors-offset-reference.json"
    )).unwrap();
    let mut schema = tantivy::schema::Schema::builder();
    let field = schema.add_text_field("body", tantivy::schema::TEXT);
    let index = TantivyIndexHandle::create_in_ram(schema.build());
    let documents = fixture["bulk"][0]["documents"].as_array().unwrap();
    assert_eq!(documents.len(), 16);
    assert_eq!(reference["rows"].as_array().unwrap().len(), documents.len());
    for source in documents {
        let mut document = TantivyDocument::default();
        add_positioned_text_values(&mut document, &index, field,
            &[&source["_source"]["body"]], 100).unwrap();
        let mut tokens = Vec::new();
        for value in document.get_all(field) {
            if let Some(pretokenized) = value.tokenized_text() {
                tokens.extend(pretokenized.tokens.clone());
            } else {
                let mut analyzer = index.tokenizer_for_field(field).unwrap();
                let mut stream = analyzer.token_stream(value.as_text().unwrap());
                while stream.advance() {
                    tokens.push(stream.token().clone());
                }
            }
        }
        let mut terms: BTreeMap<String, Vec<Value>> = BTreeMap::new();
        for token in tokens {
            terms.entry(token.text).or_default().push(serde_json::json!({
                "position": token.position,
                "start_offset": token.offset_from,
                "end_offset": token.offset_to,
            }));
        }
        let actual = terms.into_iter().map(|(term, tokens)| (term, serde_json::json!({
            "term_freq": tokens.len(), "tokens": tokens,
        }))).collect::<BTreeMap<_, _>>();
        let expected = reference["rows"].as_array().unwrap().iter()
            .find(|row| row["id"] == source["_id"]).unwrap();
        assert_eq!(serde_json::to_value(actual).unwrap(), expected["terms"], "{}", source["_id"]);
    }
}

fn assert_reference_field_statistics(state: &TantivySearchState, expected: &Value) {
    let field = state.fields["body"].field;
    let mut documents = BTreeSet::new();
    let mut sum_doc_freq = 0u64;
    let mut sum_ttf = 0u64;
    // Diagnostic enumeration verifies the native data contract, not a request-time algorithm.
    for (ordinal, segment) in state.searcher.segment_readers().iter().enumerate() {
        let inverted = segment.inverted_index(field).unwrap();
        let mut terms = inverted.terms().stream().unwrap();
        while terms.advance() {
            let mut postings = inverted.read_postings_from_terminfo(
                terms.value(), IndexRecordOption::WithFreqsAndPositions,
            ).unwrap();
            let mut doc_freq = 0u64;
            while postings.doc() != tantivy::TERMINATED {
                let doc = postings.doc();
                if segment.alive_bitset().map_or(true, |alive| alive.is_alive(doc)) {
                    documents.insert((ordinal, doc));
                    doc_freq += 1;
                    sum_ttf += u64::from(postings.term_freq());
                }
                postings.advance();
            }
            // This fixture has no deletes, so dictionary and live posting counts agree.
            assert_eq!(doc_freq, u64::from(terms.value().doc_freq));
            sum_doc_freq += doc_freq;
        }
    }
    assert_eq!(serde_json::json!({
        "doc_count": documents.len(), "sum_doc_freq": sum_doc_freq, "sum_ttf": sum_ttf,
    }), *expected);
}

fn assert_reference_positions(state: &TantivySearchState, expected: &[&Value]) {
    let field = state.fields["body"].field;
    let addresses = state.searcher.search(&AllQuery, &DocSetCollector).unwrap();
    assert_eq!(addresses.len(), expected.len());
    for address in addresses {
        let id = state.document_id_for_address(&state.searcher, address).unwrap();
        let expected = expected.iter().find(|row| row["id"] == id).unwrap();
        let segment = state.searcher.segment_reader(address.segment_ord);
        let inverted = segment.inverted_index(field).unwrap();
        let mut terms = inverted.terms().stream().unwrap();
        let mut actual = BTreeMap::new();
        while terms.advance() {
            let text = std::str::from_utf8(terms.key()).unwrap();
            let term = Term::from_field_text(field, text);
            let mut postings = inverted.read_postings(&term, IndexRecordOption::WithFreqsAndPositions)
                .unwrap().unwrap();
            if postings.doc() < address.doc_id {
                postings.seek(address.doc_id);
            }
            if postings.doc() == address.doc_id {
                let mut positions = Vec::new();
                postings.positions(&mut positions);
                actual.insert(text.to_owned(), positions);
            }
        }
        assert_eq!(serde_json::to_value(&actual).unwrap(), expected["terms"], "{id}");
        let length: usize = actual.values().map(Vec::len).sum();
        assert_eq!(segment.get_fieldnorms_reader(field).unwrap().fieldnorm(address.doc_id), length as u32);
    }
}

#[test]
fn native_array_positions_match_stored_reference_across_refreshes() {
    let fixture: Value = serde_json::from_str(include_str!(
        "../../../tools/fixtures/search-native-array-positions-compat.json"
    )).unwrap();
    let reference: Value = serde_json::from_str(include_str!(
        "../../../tools/fixtures/search-native-array-positions-reference.json"
    )).unwrap();
    let mut documents_checked = 0;
    let mut queries_checked = 0;
    for definition in fixture["indices"].as_array().unwrap() {
        let name = definition["name"].as_str().unwrap();
        let engine = TantivyEngine::default();
        engine.create_index(CreateIndexRequest {
            index: name.into(), settings: definition["body"]["settings"].clone(),
            mappings: definition["body"]["mappings"].clone(),
        }).unwrap();
        let documents = fixture["bulk"].as_array().unwrap().iter()
            .find(|bulk| bulk["index"] == name).unwrap()["documents"].as_array().unwrap();
        let expected = reference["rows"].as_array().unwrap().iter()
            .filter(|row| row["index"] == name).collect::<Vec<_>>();
        let mut old = None;
        for chunk in documents.chunks(8) {
            for document in chunk {
                engine.index_document(IndexDocumentRequest {
                    index: name.into(), id: document["_id"].as_str().unwrap().into(),
                    source: document["_source"].clone(),
                }).unwrap();
            }
            engine.refresh(RefreshRequest { indices: vec![name.into()] }).unwrap();
            if old.is_none() {
                old = engine.store.read().unwrap().indices[name].search_state.clone();
            }
        }
        let store = engine.store.read().unwrap();
        let state = store.indices[name].search_state.as_ref().unwrap();
        assert_reference_positions(state, &expected);
        assert_reference_field_statistics(state, &expected[0]["field_statistics"]);
        let old_expected = expected.iter().copied().filter(|row|
            documents[..8].iter().any(|doc| doc["_id"] == row["id"])).collect::<Vec<_>>();
        assert_reference_positions(old.as_ref().unwrap(), &old_expected);
        documents_checked += expected.len();
        let field = state.fields["body"].field;
        let total_tokens: u64 = state.searcher.segment_readers().iter().map(|segment|
            segment.inverted_index(field).unwrap().total_num_tokens()).sum();
        assert_eq!(total_tokens, 32);
        for case in fixture["cases"].as_array().unwrap().iter().filter(|case|
            case["steps"][0]["path"] == format!("/{name}/_search")) {
            let query = parse_query(&case["steps"][0]["body"]["query"]).unwrap();
            let built = build_tantivy_query(state, &query).unwrap().unwrap();
            let actual = state.searcher.search(built.as_ref(), &DocSetCollector).unwrap()
                .into_iter().map(|address| state.document_id_for_address(&state.searcher, address)
                    .unwrap().to_owned()).collect::<BTreeSet<_>>();
            let expected = reference["phrase_matches"].as_array().unwrap().iter()
                .find(|row| row["name"] == case["name"]).unwrap()["ids"].as_array().unwrap()
                .iter().map(|id| id.as_str().unwrap().to_owned()).collect::<BTreeSet<_>>();
            assert_eq!(actual, expected, "{}", case["name"]);
            queries_checked += 1;
        }
    }
    assert_eq!(documents_checked, 80);
    assert_eq!(queries_checked, 55);
}

#[test]
fn native_array_position_overflow_does_not_queue_partial_batch() {
    let engine = TantivyEngine::default();
    engine.create_index(CreateIndexRequest {
        index: "position-overflow".into(), settings: serde_json::json!({}),
        mappings: serde_json::json!({"properties":{"body":{"type":"text","position_increment_gap":2147483647}}}),
    }).unwrap();
    engine.index_document(IndexDocumentRequest {
        index: "position-overflow".into(), id: "one".into(), source: serde_json::json!({"body":"alpha"}),
    }).unwrap();
    let store = engine.store.read().unwrap();
    let index = &store.indices["position-overflow"];
    let first = Arc::new(index.documents.get("one").unwrap().clone());
    let mut invalid = first.as_ref().clone();
    invalid.metadata.id = "invalid".into();
    invalid.source = serde_json::json!({"body":["alpha","beta"]});
    let mut state = TantivySearchState::build_from_documents(&index.schema,
        std::iter::empty::<&StoredDocument>(), -1).unwrap();
    let old = state.clone();
    assert!(state.append_documents(&[Arc::clone(&first), Arc::new(invalid)]).is_err());
    state.writer.lock().unwrap().commit().unwrap();
    state.reader.reload().unwrap();
    assert_eq!(state.reader.searcher().num_docs(), 0);
    state.append_documents(&[first]).unwrap();
    assert_eq!(state.searcher.num_docs(), 1);
    assert_eq!(old.searcher.num_docs(), 0);
}
