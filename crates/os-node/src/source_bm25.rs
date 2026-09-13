use super::*;
use os_core::bm25::{source_text_tokens, FieldStatistics};

pub(super) type FieldScores = BTreeMap<String, FieldStatistics>;

pub(super) struct SourceScoring {
    groups: BTreeMap<String, BTreeMap<u32, FieldScores>>,
}

fn supports_field(mappings: &Value, field: &str) -> bool {
    let mut current = mappings;
    for segment in field.split('.') {
        if current.get("type").and_then(Value::as_str) == Some("nested") {
            return false;
        }
        let Some(next) = current
            .get("properties")
            .and_then(|fields| fields.get(segment))
        else {
            return false;
        };
        current = next;
    }
    current.get("type").and_then(Value::as_str) == Some("text")
        && [
            "analyzer",
            "search_analyzer",
            "similarity",
            "norms",
            "index_options",
            "index",
            "term_vector",
        ]
        .iter()
        .all(|key| current.get(key).is_none())
}

fn field_annotation(field: &str) -> (&str, f32) {
    field
        .rsplit_once('^')
        .and_then(|(name, value)| {
            let boost = value.parse::<f32>().ok()?;
            (!name.is_empty() && boost.is_finite()).then_some((name, boost))
        })
        .unwrap_or((field, 1.0))
}

fn collect_fields(query: &Value, fields: &mut BTreeSet<String>) {
    if let Some(spec) = query.get("multi_match") {
        match spec.get("fields") {
            Some(Value::String(field)) => {
                fields.insert(field_annotation(field).0.to_owned());
            }
            Some(Value::Array(values)) => {
                for field in values.iter().filter_map(Value::as_str) {
                    fields.insert(field_annotation(field).0.to_owned());
                }
            }
            _ => {}
        }
    }
    if let Some(spec) = query.get("match").and_then(Value::as_object) {
        fields.extend(spec.keys().cloned());
    }
    for child in child_named_query_candidates(query) {
        collect_fields(child, fields);
    }
    if let Ok(inner) = decode_wrapper_query(query) {
        collect_fields(&inner, fields);
    }
}

fn field_tokens(source: &Value, field: &str) -> Vec<String> {
    fn append(value: &Value, tokens: &mut Vec<String>) {
        match value {
            Value::String(text) => tokens.extend(source_text_tokens(text)),
            Value::Array(values) => {
                for value in values {
                    append(value, tokens);
                }
            }
            _ => {}
        }
    }
    let mut tokens = Vec::new();
    let value = source.get(field).or_else(|| {
        field
            .split('.')
            .try_fold(source, |value, segment| value.get(segment))
    });
    if let Some(value) = value {
        append(value, &mut tokens);
    }
    tokens
}

impl SourceScoring {
    pub(super) fn prepare<'a>(
        query: &Value,
        mappings: &std::collections::HashMap<String, Value>,
        documents: impl IntoIterator<Item = (&'a str, u32, &'a Value)>,
    ) -> Self {
        let mut requested = BTreeSet::new();
        collect_fields(query, &mut requested);
        let mut groups = BTreeMap::<(String, u32), BTreeMap<String, Vec<Vec<String>>>>::new();
        if requested.is_empty() {
            return Self {
                groups: BTreeMap::new(),
            };
        }
        for (index, shard, source) in documents {
            let Some(mapping) = mappings.get(index) else {
                continue;
            };
            let fields = groups.entry((index.to_owned(), shard)).or_default();
            for field in &requested {
                if supports_field(mapping, field) {
                    fields
                        .entry(field.clone())
                        .or_default()
                        .push(field_tokens(source, field));
                }
            }
        }
        let mut prepared = BTreeMap::<String, BTreeMap<u32, FieldScores>>::new();
        for ((index, shard), fields) in groups {
            prepared.entry(index).or_default().insert(
                shard,
                fields
                    .into_iter()
                    .map(|(field, docs)| {
                        (
                            field,
                            FieldStatistics::from_documents(docs.iter().map(Vec::as_slice)),
                        )
                    })
                    .collect(),
            );
        }
        Self { groups: prepared }
    }

    pub(super) fn fields(&self, index: &str, shard: u32) -> Option<&FieldScores> {
        self.groups.get(index)?.get(&shard)
    }
}

pub(super) fn evaluate(
    fields: &FieldScores,
    mappings: &Value,
    source: &Value,
    query: &Value,
) -> Option<(bool, f64)> {
    use os_query_dsl::{MultiMatchType, Query};
    if query.get("match").is_none() && query.get("multi_match").is_none() {
        return None;
    }
    if query
        .get("match")
        .and_then(Value::as_object)
        .is_some_and(|spec| {
            spec.values()
                .any(|options| options.get("analyzer").is_some())
        })
    {
        return None;
    }
    let parsed = os_query_dsl::parse_query(query).ok()?;
    let (names, tokens, boost, tie, sum) = match parsed {
        Query::Match {
            field,
            query,
            boost,
            fuzziness,
            minimum_should_match,
            operator,
            zero_terms_all,
            ..
        } if fuzziness.is_none()
            && minimum_should_match.is_none()
            && operator.as_deref().unwrap_or("or") == "or"
            && !zero_terms_all =>
        {
            (
                vec![field],
                source_text_tokens(&opensearch_object_text_value(&query)?),
                boost.unwrap_or(1.0),
                0.0,
                false,
            )
        }
        Query::MultiMatch {
            fields,
            query,
            query_type,
            boost,
            tie_breaker,
            analyzer,
            fuzziness,
            minimum_should_match,
            operator,
            zero_terms_all,
            ..
        } if matches!(
            query_type,
            MultiMatchType::BestFields | MultiMatchType::MostFields
        ) && analyzer.is_none()
            && fuzziness.is_none()
            && minimum_should_match.is_none()
            && operator.as_deref().unwrap_or("or") == "or"
            && !zero_terms_all =>
        {
            (
                fields,
                source_text_tokens(&opensearch_object_text_value(&query)?),
                boost.unwrap_or(1.0),
                tie_breaker.unwrap_or(0.0) as f32,
                query_type == MultiMatchType::MostFields,
            )
        }
        _ => return None,
    };
    let mut scores = Vec::new();
    let mut matched = false;
    for name in names {
        let (field, field_boost) = field_annotation(&name);
        if field.contains('*') || field == "_id" {
            return None;
        }
        match lookup_query_field_mapping_type(mappings, field) {
            None => continue,
            Some("text") if supports_field(mappings, field) => {}
            _ => return None,
        }
        let stats = fields.get(field)?;
        let score = stats.score(&tokens, &field_tokens(source, field));
        matched |= score > 0.0;
        scores.push(score * field_boost);
    }
    let score = if sum {
        scores.into_iter().sum::<f32>()
    } else {
        scores.sort_by(|a, b| b.total_cmp(a));
        scores.first().copied().unwrap_or(0.0) + tie * scores.iter().skip(1).sum::<f32>()
    };
    Some((matched, f64::from(score) * boost))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn shard_corpus_and_boosted_bool_scores() {
        let mapping = json!({"properties": {
            "title": {"type": "text"}, "message": {"type": "text"},
            "service": {"type": "keyword"}, "latency": {"type": "long"}
        }});
        let mappings = std::collections::HashMap::from([
            ("a".to_owned(), mapping.clone()),
            ("b".to_owned(), mapping.clone()),
        ]);
        let docs = [
            json!({"title":"alpha other other other other", "message":"other", "service":"yes", "latency":10}),
            json!({"title":"alpha other", "message":"other", "service":"yes", "latency":10}),
            json!({"title":"alpha alpha alpha", "message":"other", "service":"yes", "latency":10}),
        ];
        let unrelated = json!({"title":"beta"});
        let query = json!({"bool": {
            "must": {"multi_match": {"query":"alpha", "fields":["title^2", "message"]}},
            "should": {"term":{"service":"yes"}}, "minimum_should_match":1,
            "filter": {"range":{"latency":{"lte":100}}}
        }});
        let scoring = SourceScoring::prepare(
            &query,
            &mappings,
            docs.iter()
                .map(|doc| ("a", 0, doc))
                .chain([("a", 1, &unrelated), ("b", 0, &unrelated)]),
        );
        for (doc, expected) in docs.iter().zip([1.100778, 1.145143, 1.194936]) {
            let (matched, score) = evaluate_search_query_source_with_scoring_checked(
                doc,
                "id",
                &query,
                &mapping,
                scoring.fields("a", 0),
            )
            .unwrap()
            .unwrap();
            assert!(matched);
            assert!((score - expected).abs() < 0.000001, "{score} != {expected}");
        }
        assert_eq!(
            evaluate(
                scoring.fields("a", 1).unwrap(),
                &mapping,
                &unrelated,
                &query["bool"]["must"]
            ),
            Some((false, 0.0))
        );
    }

    #[test]
    fn tokens_arrays_dotted_fields_and_unsupported_options() {
        assert_eq!(
            field_tokens(&json!({"obj":{"text":[null,"ALPHA",["beta"]]}}), "obj.text"),
            ["alpha", "beta"]
        );
        assert!(field_tokens(&json!({"text":"alpha"}), "obj.text").is_empty());
        let mapping = json!({"properties":{"text":{"type":"text"}}});
        let doc = json!({"text":"alpha"});
        let query = json!({"match":{"text":"alpha"}});
        let mappings = std::collections::HashMap::from([("a".to_owned(), mapping.clone())]);
        let scoring = SourceScoring::prepare(&query, &mappings, [("a", 0, &doc)]);
        let fields = scoring.fields("a", 0).unwrap();
        for option in ["analyzer", "search_analyzer", "norms", "similarity"] {
            let mut custom = mapping.clone();
            custom["properties"]["text"][option] = json!("custom");
            assert!(evaluate(fields, &custom, &doc, &query).is_none());
        }
        assert!(evaluate(
            fields,
            &mapping,
            &doc,
            &json!({"match":{"text":{"query":"alpha", "analyzer":"keyword"}}})
        )
        .is_none());
        let zero_boost = json!({"multi_match":{"query":"alpha", "fields":["text^0"]}});
        assert_eq!(
            evaluate(fields, &mapping, &doc, &zero_boost),
            Some((true, 0.0))
        );
        let filter = json!({"bool":{"filter":query}});
        assert_eq!(
            evaluate_search_query_source_with_scoring_checked(
                &doc,
                "id",
                &filter,
                &mapping,
                Some(fields)
            )
            .unwrap(),
            Some((true, 0.0))
        );
        let leaf_score = evaluate(fields, &mapping, &doc, &query).unwrap().1;
        let boosted = json!({"bool":{"must":query, "boost":0.5}});
        assert_eq!(
            evaluate_search_query_source_with_scoring_checked(
                &doc,
                "id",
                &boosted,
                &mapping,
                Some(fields)
            )
            .unwrap(),
            Some((true, leaf_score * 0.5))
        );
    }
}
