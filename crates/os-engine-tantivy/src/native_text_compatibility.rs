use super::*;

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub(super) struct NativeTextCompatibility(BTreeMap<String, FieldCompatibility>);

#[derive(Clone, Debug, PartialEq, Eq)]
struct FieldCompatibility {
    supported: bool,
    has_terms: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn metadata_matches_source_guard_for_mixed_inputs_and_snapshots() {
        let values = vec![
            Value::Null,
            serde_json::json!(""),
            serde_json::json!("alpha beta"),
            serde_json::json!("Alpha-42 !!!"),
            serde_json::json!("a".repeat(39)),
            serde_json::json!("a".repeat(40)),
            serde_json::json!("\u{e9}"),
            serde_json::json!(42),
            serde_json::json!(true),
            serde_json::json!({"x":"alpha"}),
            serde_json::json!([]),
            serde_json::json!([null, ["alpha", "beta"]]),
            serde_json::json!(["alpha", false]),
        ];
        for left in &values {
            for right in &values {
                let mut metadata = NativeTextCompatibility(BTreeMap::from([(
                    "title".into(),
                    FieldCompatibility {
                        supported: true,
                        has_terms: false,
                    },
                )]));
                metadata.observe(&serde_json::json!({"title":left}));
                let snapshot = metadata.clone();
                metadata.observe(&serde_json::json!({"title":right}));
                let supported = [left, right].iter().all(|value| {
                    native_phrase_source_value_supported(value)
                        && tokens_for_source_value(value)
                            .iter()
                            .all(|token| token.len() < 40)
                });
                let has_terms = [left, right]
                    .iter()
                    .any(|value| !tokens_for_source_value(value).is_empty());
                assert_eq!(
                    metadata.supports("title"),
                    supported && has_terms,
                    "{left} {right}"
                );
                assert_eq!(
                    snapshot.supports("title"),
                    native_phrase_source_value_supported(left)
                        && tokens_for_source_value(left)
                            .iter()
                            .all(|token| token.len() < 40)
                        && !tokens_for_source_value(left).is_empty()
                );
                assert!(!metadata.supports("missing"));
            }
        }
    }
}

impl NativeTextCompatibility {
    pub(super) fn new(fields: &BTreeMap<String, TantivyIndexedField>) -> Self {
        Self(
            fields
                .iter()
                .filter(|(name, field)| {
                    !name.contains('.')
                        && field.field_type == TantivyFieldType::Text
                        && field.multi_field_source.is_none()
                })
                .map(|(name, _)| {
                    (
                        name.clone(),
                        FieldCompatibility {
                            supported: true,
                            has_terms: false,
                        },
                    )
                })
                .collect(),
        )
    }

    pub(super) fn observe(&mut self, source: &Value) {
        for (field, compatibility) in &mut self.0 {
            if !compatibility.supported {
                continue;
            }
            let Some(value) = source.get(field) else {
                continue;
            };
            let (supported, has_terms) = phrase_source_compatibility(value);
            compatibility.supported &= supported;
            compatibility.has_terms |= has_terms;
        }
    }

    pub(super) fn supports(&self, field: &str) -> bool {
        self.0
            .get(field)
            .is_some_and(|value| value.supported && value.has_terms)
    }
}

fn phrase_source_compatibility(value: &Value) -> (bool, bool) {
    match value {
        Value::Null => (true, false),
        Value::Bool(_) => (true, true),
        Value::Number(number) => phrase_text_compatibility(&number.to_string()),
        Value::String(text) if text.is_ascii() => phrase_text_compatibility(text),
        Value::String(_) | Value::Object(_) => (false, false),
        Value::Array(values) => {
            let mut has_terms = false;
            for value in values {
                let (supported, value_has_terms) = phrase_source_compatibility(value);
                if !supported {
                    return (false, false);
                }
                has_terms |= value_has_terms;
            }
            (true, has_terms)
        }
    }
}

fn phrase_text_compatibility(text: &str) -> (bool, bool) {
    let mut has_terms = false;
    for token in text.split(|character: char| !character.is_alphanumeric()) {
        if token.is_empty() {
            continue;
        }
        if token.len() >= 40 {
            return (false, false);
        }
        has_terms = true;
    }
    (true, has_terms)
}
