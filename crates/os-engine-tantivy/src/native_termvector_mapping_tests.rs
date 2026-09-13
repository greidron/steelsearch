use super::*;

#[test]
fn text_term_vector_modes_are_retained_by_field_mappings() {
    let modes = [
        ("default", None),
        ("no", Some("no")),
        ("yes", Some("yes")),
        ("with_positions", Some("with_positions")),
        ("with_offsets", Some("with_offsets")),
        ("with_positions_offsets", Some("with_positions_offsets")),
        ("with_positions_payloads", Some("with_positions_payloads")),
        (
            "with_positions_offsets_payloads",
            Some("with_positions_offsets_payloads"),
        ),
    ];
    let properties: serde_json::Map<String, Value> = modes
        .iter()
        .map(|(name, mode)| {
            let mut mapping = serde_json::json!({"type": "text"});
            if let Some(mode) = mode {
                mapping["term_vector"] = serde_json::json!(mode);
            }
            ((*name).to_string(), mapping)
        })
        .collect();
    let fields = read_field_mappings(&serde_json::json!({"properties": properties})).unwrap();

    for (name, expected) in modes {
        let field = fields.iter().find(|field| field.name == name).unwrap();
        let options = field.text_options.as_ref().unwrap();
        assert_eq!(
            options.term_vector.as_ref().and_then(Value::as_str),
            expected
        );
    }
}

#[test]
fn text_term_vector_retention_survives_nested_and_multi_field_mapping_serialization() {
    let fields = read_field_mappings(&serde_json::json!({"properties": {
        "article": {"properties": {
            "body": {"type": "text", "term_vector": "with_offsets"},
            "title": {"type": "text", "fields": {
                "phrases": {"type": "text", "term_vector": "with_positions_offsets"}
            }}
        }}
    }}))
    .unwrap();

    for (name, expected) in [
        ("article.body", "with_offsets"),
        ("article.title.phrases", "with_positions_offsets"),
    ] {
        let field = fields.iter().find(|field| field.name == name).unwrap();
        assert_eq!(
            field.text_options.as_ref().unwrap().term_vector,
            Some(serde_json::json!(expected))
        );
        let serialized = serde_json::to_value(field).unwrap();
        assert_eq!(serialized["text_options"]["term_vector"], expected);
        assert_eq!(
            serde_json::from_value::<TantivyFieldMapping>(serialized).unwrap(),
            field.clone()
        );
    }
}

#[test]
fn legacy_text_mapping_snapshot_without_term_vector_deserializes_to_none() {
    let snapshot = serde_json::json!({
        "name": "body",
        "field_type": "text",
        "indexed": true,
        "stored": false,
        "fast": false,
        "text_options": {"analyzer": "standard"}
    });

    let field: TantivyFieldMapping = serde_json::from_value(snapshot.clone()).unwrap();
    assert_eq!(field.text_options.as_ref().unwrap().term_vector, None);
    assert_eq!(serde_json::to_value(field).unwrap(), snapshot);
}
