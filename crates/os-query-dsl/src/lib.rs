//! OpenSearch query DSL model placeholders.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use thiserror::Error;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Query {
    MatchAll,
    MatchNone,
    Term {
        field: String,
        value: serde_json::Value,
    },
    Terms {
        field: String,
        values: Vec<serde_json::Value>,
    },
    Match {
        field: String,
        query: serde_json::Value,
    },
    Range {
        field: String,
        bounds: RangeBounds,
    },
    Exists {
        field: String,
    },
    Ids {
        values: Vec<String>,
    },
    Prefix {
        field: String,
        value: String,
        case_insensitive: bool,
    },
    Wildcard {
        field: String,
        value: String,
        case_insensitive: bool,
    },
    Knn(KnnQuery),
    Bool {
        clauses: BoolQuery,
    },
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct KnnQuery {
    pub field: String,
    pub vector: Vec<f32>,
    pub k: usize,
    pub filter: Option<Box<Query>>,
    pub ignore_unmapped: bool,
    pub max_distance: Option<f32>,
    pub min_score: Option<f32>,
    pub method_parameters: BTreeMap<String, Value>,
    pub rescore: Option<Value>,
    pub expand_nested_docs: bool,
}

#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct RangeBounds {
    pub gt: Option<serde_json::Value>,
    pub gte: Option<serde_json::Value>,
    pub lt: Option<serde_json::Value>,
    pub lte: Option<serde_json::Value>,
}

#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct BoolQuery {
    pub must: Vec<Query>,
    pub should: Vec<Query>,
    pub filter: Vec<Query>,
    pub must_not: Vec<Query>,
    pub minimum_should_match: Option<u32>,
}

pub type AggregationMap = BTreeMap<String, Aggregation>;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Aggregation {
    Terms(TermsAggregation),
    Metric(MetricAggregation),
    Filter(FilterAggregation),
    Filters(FiltersAggregation),
    TopHits(TopHitsAggregation),
    Composite(CompositeAggregation),
    SignificantTerms(SignificantTermsAggregation),
    GeoBounds(GeoBoundsAggregation),
    Pipeline(PipelineAggregation),
    ScriptedMetric(ScriptedMetricAggregation),
    Plugin(PluginAggregation),
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct TermsAggregation {
    pub field: String,
    pub size: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MetricAggregationKind {
    Min,
    Max,
    Sum,
    Avg,
    ValueCount,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MetricAggregation {
    pub kind: MetricAggregationKind,
    pub field: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct FilterAggregation {
    pub filter: Query,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct FiltersAggregation {
    pub filters: BTreeMap<String, Query>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct TopHitsAggregation {
    pub from: usize,
    pub size: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CompositeAggregation {
    pub size: usize,
    pub sources: Vec<CompositeTermsSource>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CompositeTermsSource {
    pub name: String,
    pub field: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SignificantTermsAggregation {
    pub field: String,
    pub size: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct GeoBoundsAggregation {
    pub field: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct PipelineAggregation {
    pub kind: PipelineAggregationKind,
    pub buckets_path: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PipelineAggregationKind {
    SumBucket,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ScriptedMetricAggregation {
    pub value: Option<Value>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct PluginAggregation {
    pub name: String,
    pub kind: String,
    pub params: Value,
}

#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct AggregationResponse {
    pub aggregations: BTreeMap<String, AggregationResult>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AggregationResult {
    Terms(TermsAggregationResult),
    Metric(MetricAggregationResult),
    Filter(FilterAggregationResult),
    Filters(FiltersAggregationResult),
    TopHits(TopHitsAggregationResult),
    Composite(CompositeAggregationResult),
    SignificantTerms(SignificantTermsAggregationResult),
    GeoBounds(GeoBoundsAggregationResult),
    Pipeline(PipelineAggregationResult),
    ScriptedMetric(ScriptedMetricAggregationResult),
    Plugin(PluginAggregationResult),
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct TermsAggregationResult {
    pub buckets: Vec<TermsBucket>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct TermsBucket {
    pub key: Value,
    pub doc_count: u64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct MetricAggregationResult {
    pub value: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct FilterAggregationResult {
    pub doc_count: u64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct FiltersAggregationResult {
    pub buckets: BTreeMap<String, FilterAggregationResult>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct TopHitsAggregationResult {
    pub hits: Value,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct CompositeAggregationResult {
    pub buckets: Vec<CompositeBucket>,
    pub after_key: Option<Value>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct CompositeBucket {
    pub key: Value,
    pub doc_count: u64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct SignificantTermsAggregationResult {
    pub buckets: Vec<SignificantTermsBucket>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct SignificantTermsBucket {
    pub key: Value,
    pub doc_count: u64,
    pub bg_count: u64,
    pub score: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct GeoBoundsAggregationResult {
    pub top_left: Value,
    pub bottom_right: Value,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct PipelineAggregationResult {
    pub value: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ScriptedMetricAggregationResult {
    pub value: Option<Value>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct PluginAggregationResult {
    pub value: Value,
}

#[derive(Clone, Debug, Eq, Error, PartialEq)]
pub enum QueryDslError {
    #[error("query must be a JSON object")]
    ExpectedObject,
    #[error("query clause [{clause}] field [{field}] must be a JSON array")]
    ExpectedArray { clause: String, field: String },
    #[error("query object must contain exactly one query clause")]
    ExpectedSingleClause,
    #[error("query clause [{clause}] must contain exactly one field")]
    ExpectedSingleField { clause: String },
    #[error("query clause [{clause}] is missing required field [{field}]")]
    MissingField { clause: String, field: String },
    #[error("unsupported option [{option}] in query clause [{clause}]")]
    UnsupportedOption { clause: String, option: String },
    #[error("unsupported query clause [{clause}]")]
    UnsupportedClause { clause: String },
    #[error("invalid value for query clause [{clause}] field [{field}]: {reason}")]
    InvalidValue {
        clause: String,
        field: String,
        reason: String,
    },
}

pub type QueryDslResult<T> = std::result::Result<T, QueryDslError>;

pub fn parse_query(value: &Value) -> QueryDslResult<Query> {
    let object = value.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if object.len() != 1 {
        return Err(QueryDslError::ExpectedSingleClause);
    }

    let (clause, body) = object.iter().next().expect("checked len");
    match clause.as_str() {
        "match_all" => parse_match_all(body),
        "match_none" => parse_match_none(body),
        "term" => parse_term(body),
        "terms" => parse_terms(body),
        "match" => parse_match(body),
        "range" => parse_range(body),
        "exists" => parse_exists(body),
        "ids" => parse_ids(body),
        "prefix" => parse_prefix(body),
        "wildcard" => parse_wildcard(body),
        "knn" => parse_knn(body),
        "bool" => parse_bool(body),
        _ => Err(QueryDslError::UnsupportedClause {
            clause: clause.clone(),
        }),
    }
}

pub fn parse_search_aggregations(search_body: &Value) -> QueryDslResult<AggregationMap> {
    let object = search_body
        .as_object()
        .ok_or(QueryDslError::ExpectedObject)?;
    let aggregations = object
        .get("aggs")
        .or_else(|| object.get("aggregations"))
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "search".to_string(),
            field: "aggs".to_string(),
        })?;

    parse_aggregation_map(aggregations)
}

pub fn parse_aggregation_map(value: &Value) -> QueryDslResult<AggregationMap> {
    let object = value.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let mut aggregations = BTreeMap::new();

    for (name, body) in object {
        aggregations.insert(name.clone(), parse_aggregation(body)?);
    }

    Ok(aggregations)
}

fn parse_aggregation(value: &Value) -> QueryDslResult<Aggregation> {
    let object = value.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if object.len() != 1 {
        return Err(QueryDslError::ExpectedSingleClause);
    }

    let (kind, body) = object.iter().next().expect("checked len");
    match kind.as_str() {
        "terms" => parse_terms_aggregation(body),
        "min" => parse_metric_aggregation(MetricAggregationKind::Min, kind, body),
        "max" => parse_metric_aggregation(MetricAggregationKind::Max, kind, body),
        "sum" => parse_metric_aggregation(MetricAggregationKind::Sum, kind, body),
        "avg" => parse_metric_aggregation(MetricAggregationKind::Avg, kind, body),
        "value_count" => parse_metric_aggregation(MetricAggregationKind::ValueCount, kind, body),
        "filter" => parse_filter_aggregation(body),
        "filters" => parse_filters_aggregation(body),
        "top_hits" => parse_top_hits_aggregation(body),
        "composite" => parse_composite_aggregation(body),
        "significant_terms" => parse_significant_terms_aggregation(body),
        "geo_bounds" => parse_geo_bounds_aggregation(body),
        "sum_bucket" => parse_pipeline_aggregation(PipelineAggregationKind::SumBucket, kind, body),
        "scripted_metric" => parse_scripted_metric_aggregation(body),
        "plugin" => parse_plugin_aggregation(body),
        _ => Err(QueryDslError::UnsupportedClause {
            clause: kind.clone(),
        }),
    }
}

fn parse_terms_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let (field, size) = parse_field_size_aggregation_options("terms", body)?;
    Ok(Aggregation::Terms(TermsAggregation { field, size }))
}

fn parse_significant_terms_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let (field, size) = parse_field_size_aggregation_options("significant_terms", body)?;
    Ok(Aggregation::SignificantTerms(SignificantTermsAggregation {
        field,
        size,
    }))
}

fn parse_metric_aggregation(
    kind: MetricAggregationKind,
    clause: &str,
    body: &Value,
) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let field = object
        .get("field")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: clause.to_string(),
            field: "field".to_string(),
        })?
        .to_string();

    for option in object.keys() {
        if option != "field" {
            return Err(QueryDslError::UnsupportedOption {
                clause: clause.to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Aggregation::Metric(MetricAggregation { kind, field }))
}

fn parse_geo_bounds_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let field = object
        .get("field")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "geo_bounds".to_string(),
            field: "field".to_string(),
        })?
        .to_string();

    for option in object.keys() {
        if option != "field" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "geo_bounds".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Aggregation::GeoBounds(GeoBoundsAggregation { field }))
}

fn parse_pipeline_aggregation(
    kind: PipelineAggregationKind,
    clause: &str,
    body: &Value,
) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let buckets_path = object
        .get("buckets_path")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: clause.to_string(),
            field: "buckets_path".to_string(),
        })?
        .to_string();

    for option in object.keys() {
        if option != "buckets_path" {
            return Err(QueryDslError::UnsupportedOption {
                clause: clause.to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Aggregation::Pipeline(PipelineAggregation {
        kind,
        buckets_path,
    }))
}

fn parse_scripted_metric_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let mut value = None;

    for (option, option_value) in object {
        match option.as_str() {
            "init_script" | "map_script" | "combine_script" | "reduce_script" => {}
            "params" => {
                let params = option_value
                    .as_object()
                    .ok_or(QueryDslError::ExpectedObject)?;
                value = params.get("value").cloned();
            }
            _ => {
                return Err(QueryDslError::UnsupportedOption {
                    clause: "scripted_metric".to_string(),
                    option: option.clone(),
                });
            }
        }
    }

    Ok(Aggregation::ScriptedMetric(ScriptedMetricAggregation {
        value,
    }))
}

fn parse_plugin_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let name = object
        .get("name")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "plugin".to_string(),
            field: "name".to_string(),
        })?
        .to_string();
    let kind = object
        .get("kind")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "plugin".to_string(),
            field: "kind".to_string(),
        })?
        .to_string();
    let params = object
        .get("params")
        .cloned()
        .unwrap_or_else(|| serde_json::json!({}));

    for option in object.keys() {
        match option.as_str() {
            "name" | "kind" | "params" => {}
            _ => {
                return Err(QueryDslError::UnsupportedOption {
                    clause: "plugin".to_string(),
                    option: option.clone(),
                });
            }
        }
    }

    Ok(Aggregation::Plugin(PluginAggregation {
        name,
        kind,
        params,
    }))
}

fn parse_filter_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    Ok(Aggregation::Filter(FilterAggregation {
        filter: parse_query(body)?,
    }))
}

fn parse_filters_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let filters = object
        .get("filters")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "filters".to_string(),
            field: "filters".to_string(),
        })?
        .as_object()
        .ok_or(QueryDslError::ExpectedObject)?;

    for option in object.keys() {
        if option != "filters" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "filters".to_string(),
                option: option.clone(),
            });
        }
    }

    let mut parsed = BTreeMap::new();
    for (name, query) in filters {
        parsed.insert(name.clone(), parse_query(query)?);
    }
    Ok(Aggregation::Filters(FiltersAggregation { filters: parsed }))
}

fn parse_top_hits_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let mut from = 0;
    let mut size = 3;

    for (option, value) in object {
        match option.as_str() {
            "from" => from = parse_usize_option("top_hits", "from", value)?,
            "size" => size = parse_usize_option("top_hits", "size", value)?,
            _ => {
                return Err(QueryDslError::UnsupportedOption {
                    clause: "top_hits".to_string(),
                    option: option.clone(),
                });
            }
        }
    }

    Ok(Aggregation::TopHits(TopHitsAggregation { from, size }))
}

fn parse_composite_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let mut size = 10;
    let mut sources = None;

    for (option, value) in object {
        match option.as_str() {
            "size" => size = parse_usize_option("composite", "size", value)?,
            "sources" => {
                sources = Some(parse_composite_sources(value)?);
            }
            _ => {
                return Err(QueryDslError::UnsupportedOption {
                    clause: "composite".to_string(),
                    option: option.clone(),
                });
            }
        }
    }

    Ok(Aggregation::Composite(CompositeAggregation {
        size,
        sources: sources.ok_or_else(|| QueryDslError::MissingField {
            clause: "composite".to_string(),
            field: "sources".to_string(),
        })?,
    }))
}

fn parse_composite_sources(value: &Value) -> QueryDslResult<Vec<CompositeTermsSource>> {
    let sources = value
        .as_array()
        .ok_or_else(|| QueryDslError::ExpectedArray {
            clause: "composite".to_string(),
            field: "sources".to_string(),
        })?;
    let mut parsed = Vec::new();

    for source in sources {
        let source = source.as_object().ok_or(QueryDslError::ExpectedObject)?;
        if source.len() != 1 {
            return Err(QueryDslError::ExpectedSingleField {
                clause: "composite".to_string(),
            });
        }
        let (name, source_body) = source.iter().next().expect("checked len");
        let source_body = source_body
            .as_object()
            .ok_or(QueryDslError::ExpectedObject)?;
        if source_body.len() != 1 {
            return Err(QueryDslError::ExpectedSingleClause);
        }
        let (source_kind, terms_body) = source_body.iter().next().expect("checked len");
        if source_kind != "terms" {
            return Err(QueryDslError::UnsupportedClause {
                clause: source_kind.clone(),
            });
        }
        let terms_body = terms_body
            .as_object()
            .ok_or(QueryDslError::ExpectedObject)?;
        let field = terms_body
            .get("field")
            .and_then(Value::as_str)
            .ok_or_else(|| QueryDslError::MissingField {
                clause: "composite.terms".to_string(),
                field: "field".to_string(),
            })?
            .to_string();
        for option in terms_body.keys() {
            if option != "field" {
                return Err(QueryDslError::UnsupportedOption {
                    clause: "composite.terms".to_string(),
                    option: option.clone(),
                });
            }
        }
        parsed.push(CompositeTermsSource {
            name: name.clone(),
            field,
        });
    }

    Ok(parsed)
}

fn parse_usize_option(clause: &str, option: &str, value: &Value) -> QueryDslResult<usize> {
    if let Some(value) = value.as_u64() {
        return usize::try_from(value).map_err(|_| QueryDslError::UnsupportedOption {
            clause: clause.to_string(),
            option: option.to_string(),
        });
    }

    Err(QueryDslError::UnsupportedOption {
        clause: clause.to_string(),
        option: option.to_string(),
    })
}

fn parse_field_size_aggregation_options(
    clause: &str,
    body: &Value,
) -> QueryDslResult<(String, usize)> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let field = object
        .get("field")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: clause.to_string(),
            field: "field".to_string(),
        })?
        .to_string();
    let mut size = 10;

    for (option, value) in object {
        match option.as_str() {
            "field" => {}
            "size" => size = parse_usize_option(clause, "size", value)?,
            _ => {
                return Err(QueryDslError::UnsupportedOption {
                    clause: clause.to_string(),
                    option: option.clone(),
                });
            }
        }
    }

    Ok((field, size))
}

fn parse_match_all(body: &Value) -> QueryDslResult<Query> {
    if !body.as_object().is_some_and(|object| object.is_empty()) {
        return Err(QueryDslError::ExpectedSingleClause);
    }
    Ok(Query::MatchAll)
}

fn parse_match_none(body: &Value) -> QueryDslResult<Query> {
    if !body.as_object().is_some_and(|object| object.is_empty()) {
        return Err(QueryDslError::ExpectedSingleClause);
    }
    Ok(Query::MatchNone)
}

fn parse_knn(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if let Some(field) = object.get("field").and_then(Value::as_str) {
        let vector = object
            .get("vector")
            .or_else(|| object.get("query_vector"))
            .ok_or_else(|| QueryDslError::MissingField {
                clause: "knn".to_string(),
                field: "vector".to_string(),
            })?;
        return parse_knn_options(field, vector, object);
    }

    if object.len() != 1 {
        return Err(QueryDslError::ExpectedSingleField {
            clause: "knn".to_string(),
        });
    }
    let (field, options) = object.iter().next().expect("checked len");
    let options = options.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let vector = options
        .get("vector")
        .or_else(|| options.get("query_vector"))
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "knn".to_string(),
            field: "vector".to_string(),
        })?;
    parse_knn_options(field, vector, options)
}

fn parse_knn_options(
    field: &str,
    vector: &Value,
    options: &serde_json::Map<String, Value>,
) -> QueryDslResult<Query> {
    for option in options.keys() {
        if !matches!(
            option.as_str(),
            "field"
                | "vector"
                | "query_vector"
                | "k"
                | "filter"
                | "ignore_unmapped"
                | "max_distance"
                | "min_score"
                | "method_parameters"
                | "rescore"
                | "expand_nested"
                | "expand_nested_docs"
        ) {
            return Err(QueryDslError::UnsupportedOption {
                clause: "knn".to_string(),
                option: option.clone(),
            });
        }
    }

    let k = options
        .get("k")
        .and_then(Value::as_u64)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "knn".to_string(),
            field: "k".to_string(),
        })
        .and_then(|value| {
            usize::try_from(value).map_err(|_| QueryDslError::InvalidValue {
                clause: "knn".to_string(),
                field: "k".to_string(),
                reason: "must fit in usize".to_string(),
            })
        })?;
    if k == 0 {
        return Err(QueryDslError::InvalidValue {
            clause: "knn".to_string(),
            field: "k".to_string(),
            reason: "must be greater than zero".to_string(),
        });
    }

    let method_parameters = options
        .get("method_parameters")
        .map(|value| {
            value
                .as_object()
                .ok_or(QueryDslError::ExpectedObject)
                .map(|object| {
                    object
                        .iter()
                        .map(|(key, value)| (key.clone(), value.clone()))
                        .collect()
                })
        })
        .transpose()?
        .unwrap_or_default();

    Ok(Query::Knn(KnnQuery {
        field: field.to_string(),
        vector: parse_f32_array("knn", "vector", vector)?,
        k,
        filter: options
            .get("filter")
            .map(parse_query)
            .transpose()?
            .map(Box::new),
        ignore_unmapped: options
            .get("ignore_unmapped")
            .and_then(Value::as_bool)
            .unwrap_or(false),
        max_distance: optional_f32(options.get("max_distance"), "max_distance")?,
        min_score: optional_f32(options.get("min_score"), "min_score")?,
        method_parameters,
        rescore: options.get("rescore").cloned(),
        expand_nested_docs: options
            .get("expand_nested")
            .or_else(|| options.get("expand_nested_docs"))
            .and_then(Value::as_bool)
            .unwrap_or(false),
    }))
}

fn parse_f32_array(clause: &str, field: &str, value: &Value) -> QueryDslResult<Vec<f32>> {
    let values = value
        .as_array()
        .ok_or_else(|| QueryDslError::ExpectedArray {
            clause: clause.to_string(),
            field: field.to_string(),
        })?;
    values
        .iter()
        .map(|value| {
            value
                .as_f64()
                .map(|value| value as f32)
                .ok_or_else(|| QueryDslError::InvalidValue {
                    clause: clause.to_string(),
                    field: field.to_string(),
                    reason: "must contain only numbers".to_string(),
                })
        })
        .collect()
}

fn optional_f32(value: Option<&Value>, field: &str) -> QueryDslResult<Option<f32>> {
    value
        .map(|value| {
            value
                .as_f64()
                .map(|value| value as f32)
                .ok_or_else(|| QueryDslError::InvalidValue {
                    clause: "knn".to_string(),
                    field: field.to_string(),
                    reason: "must be a number".to_string(),
                })
        })
        .transpose()
}

fn parse_term(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if object.len() != 1 {
        return Err(QueryDslError::ExpectedSingleField {
            clause: "term".to_string(),
        });
    }

    let (field, term_body) = object.iter().next().expect("checked len");
    let value = if let Some(object) = term_body.as_object() {
        object
            .get("value")
            .cloned()
            .ok_or_else(|| QueryDslError::MissingField {
                clause: "term".to_string(),
                field: "value".to_string(),
            })?
    } else {
        term_body.clone()
    };

    Ok(Query::Term {
        field: field.clone(),
        value,
    })
}

fn parse_terms(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if object.len() != 1 {
        return Err(QueryDslError::ExpectedSingleField {
            clause: "terms".to_string(),
        });
    }

    let (field, values_body) = object.iter().next().expect("checked len");
    let values = values_body
        .as_array()
        .ok_or(QueryDslError::ExpectedObject)?
        .clone();

    Ok(Query::Terms {
        field: field.clone(),
        values,
    })
}

fn parse_match(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if object.len() != 1 {
        return Err(QueryDslError::ExpectedSingleField {
            clause: "match".to_string(),
        });
    }

    let (field, match_body) = object.iter().next().expect("checked len");
    let query = if let Some(object) = match_body.as_object() {
        object
            .get("query")
            .cloned()
            .ok_or_else(|| QueryDslError::MissingField {
                clause: "match".to_string(),
                field: "query".to_string(),
            })?
    } else {
        match_body.clone()
    };

    Ok(Query::Match {
        field: field.clone(),
        query,
    })
}

fn parse_exists(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let field = object
        .get("field")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "exists".to_string(),
            field: "field".to_string(),
        })?
        .to_string();

    for (option, _) in object {
        if option != "field" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "exists".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::Exists { field })
}

fn parse_ids(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let values = object
        .get("values")
        .and_then(Value::as_array)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "ids".to_string(),
            field: "values".to_string(),
        })?
        .iter()
        .map(|value| {
            value
                .as_str()
                .map(ToString::to_string)
                .ok_or(QueryDslError::ExpectedObject)
        })
        .collect::<QueryDslResult<Vec<_>>>()?;

    for (option, _) in object {
        if option != "values" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "ids".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::Ids { values })
}

fn parse_prefix(body: &Value) -> QueryDslResult<Query> {
    let (field, value, case_insensitive) = parse_string_multiterm("prefix", body, &["value"])?;
    Ok(Query::Prefix {
        field,
        value,
        case_insensitive,
    })
}

fn parse_wildcard(body: &Value) -> QueryDslResult<Query> {
    let (field, value, case_insensitive) =
        parse_string_multiterm("wildcard", body, &["value", "wildcard"])?;
    Ok(Query::Wildcard {
        field,
        value,
        case_insensitive,
    })
}

fn parse_string_multiterm(
    clause: &str,
    body: &Value,
    value_fields: &[&str],
) -> QueryDslResult<(String, String, bool)> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if object.len() != 1 {
        return Err(QueryDslError::ExpectedSingleField {
            clause: clause.to_string(),
        });
    }

    let (field, query_body) = object.iter().next().expect("checked len");
    if let Some(value) = query_body.as_str() {
        return Ok((field.clone(), value.to_string(), false));
    }

    let query_object = query_body
        .as_object()
        .ok_or(QueryDslError::ExpectedObject)?;
    let value = value_fields
        .iter()
        .find_map(|name| query_object.get(*name).and_then(Value::as_str))
        .ok_or_else(|| QueryDslError::MissingField {
            clause: clause.to_string(),
            field: value_fields[0].to_string(),
        })?
        .to_string();
    let mut case_insensitive = false;

    for (option, option_value) in query_object {
        if value_fields.contains(&option.as_str()) {
            continue;
        }
        match option.as_str() {
            "case_insensitive" => {
                case_insensitive =
                    option_value
                        .as_bool()
                        .ok_or_else(|| QueryDslError::UnsupportedOption {
                            clause: clause.to_string(),
                            option: option.clone(),
                        })?;
            }
            _ => {
                return Err(QueryDslError::UnsupportedOption {
                    clause: clause.to_string(),
                    option: option.clone(),
                });
            }
        }
    }

    Ok((field.clone(), value, case_insensitive))
}

fn parse_range(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if object.len() != 1 {
        return Err(QueryDslError::ExpectedSingleField {
            clause: "range".to_string(),
        });
    }

    let (field, range_body) = object.iter().next().expect("checked len");
    let range_object = range_body
        .as_object()
        .ok_or(QueryDslError::ExpectedObject)?;
    let mut bounds = RangeBounds::default();

    for (option, value) in range_object {
        match option.as_str() {
            "gt" => bounds.gt = Some(value.clone()),
            "gte" => bounds.gte = Some(value.clone()),
            "lt" => bounds.lt = Some(value.clone()),
            "lte" => bounds.lte = Some(value.clone()),
            _ => {
                return Err(QueryDslError::UnsupportedOption {
                    clause: "range".to_string(),
                    option: option.clone(),
                });
            }
        }
    }

    Ok(Query::Range {
        field: field.clone(),
        bounds,
    })
}

fn parse_bool(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let mut clauses = BoolQuery::default();

    for (option, value) in object {
        match option.as_str() {
            "must" => clauses.must = parse_bool_clause_value(value)?,
            "should" => clauses.should = parse_bool_clause_value(value)?,
            "filter" => clauses.filter = parse_bool_clause_value(value)?,
            "must_not" => clauses.must_not = parse_bool_clause_value(value)?,
            "minimum_should_match" => {
                clauses.minimum_should_match = Some(parse_minimum_should_match(value)?);
            }
            _ => {
                return Err(QueryDslError::UnsupportedOption {
                    clause: "bool".to_string(),
                    option: option.clone(),
                });
            }
        }
    }

    Ok(Query::Bool { clauses })
}

fn parse_bool_clause_value(value: &Value) -> QueryDslResult<Vec<Query>> {
    if let Some(values) = value.as_array() {
        values.iter().map(parse_query).collect()
    } else {
        Ok(vec![parse_query(value)?])
    }
}

fn parse_minimum_should_match(value: &Value) -> QueryDslResult<u32> {
    if let Some(value) = value.as_u64() {
        return u32::try_from(value).map_err(|_| QueryDslError::ExpectedObject);
    }

    let value = value.as_str().ok_or(QueryDslError::ExpectedObject)?;
    value.parse().map_err(|_| QueryDslError::ExpectedObject)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_match_all_query() {
        let query = parse_query(&serde_json::json!({
            "match_all": {}
        }))
        .unwrap();

        assert_eq!(query, Query::MatchAll);
    }

    #[test]
    fn parses_match_none_query() {
        let query = parse_query(&serde_json::json!({
            "match_none": {}
        }))
        .unwrap();

        assert_eq!(query, Query::MatchNone);
    }

    #[test]
    fn parses_knn_query_with_filter_and_method_parameters() {
        let query = parse_query(&serde_json::json!({
            "knn": {
                "embedding": {
                    "vector": [1.0, 0.0, 0.0],
                    "k": 2,
                    "filter": { "term": { "tenant": "a" } },
                    "ignore_unmapped": true,
                    "max_distance": 1.5,
                    "method_parameters": { "ef_search": 32 },
                    "rescore": { "oversample_factor": 2.0 },
                    "expand_nested_docs": true
                }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::Knn(KnnQuery {
                field: "embedding".to_string(),
                vector: vec![1.0, 0.0, 0.0],
                k: 2,
                filter: Some(Box::new(Query::Term {
                    field: "tenant".to_string(),
                    value: serde_json::json!("a")
                })),
                ignore_unmapped: true,
                max_distance: Some(1.5),
                min_score: None,
                method_parameters: BTreeMap::from([(
                    "ef_search".to_string(),
                    serde_json::json!(32)
                )]),
                rescore: Some(serde_json::json!({ "oversample_factor": 2.0 })),
                expand_nested_docs: true,
            })
        );
    }

    #[test]
    fn parses_short_term_query() {
        let query = parse_query(&serde_json::json!({
            "term": {
                "service": "api"
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::Term {
                field: "service".to_string(),
                value: serde_json::json!("api")
            }
        );
    }

    #[test]
    fn parses_term_query_with_value_object() {
        let query = parse_query(&serde_json::json!({
            "term": {
                "status": {
                    "value": 200
                }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::Term {
                field: "status".to_string(),
                value: serde_json::json!(200)
            }
        );
    }

    #[test]
    fn parses_terms_query() {
        let query = parse_query(&serde_json::json!({
            "terms": {
                "service": ["api", "worker"]
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::Terms {
                field: "service".to_string(),
                values: vec![serde_json::json!("api"), serde_json::json!("worker")]
            }
        );
    }

    #[test]
    fn parses_exists_query() {
        let query = parse_query(&serde_json::json!({
            "exists": {
                "field": "message"
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::Exists {
                field: "message".to_string()
            }
        );
    }

    #[test]
    fn parses_ids_query() {
        let query = parse_query(&serde_json::json!({
            "ids": {
                "values": ["1", "2"]
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::Ids {
                values: vec!["1".to_string(), "2".to_string()]
            }
        );
    }

    #[test]
    fn parses_prefix_and_wildcard_queries() {
        let prefix = parse_query(&serde_json::json!({
            "prefix": {
                "service": {
                    "value": "ap",
                    "case_insensitive": true
                }
            }
        }))
        .unwrap();
        let wildcard = parse_query(&serde_json::json!({
            "wildcard": {
                "message": "err*"
            }
        }))
        .unwrap();

        assert_eq!(
            prefix,
            Query::Prefix {
                field: "service".to_string(),
                value: "ap".to_string(),
                case_insensitive: true
            }
        );
        assert_eq!(
            wildcard,
            Query::Wildcard {
                field: "message".to_string(),
                value: "err*".to_string(),
                case_insensitive: false
            }
        );
    }

    #[test]
    fn parses_short_match_query() {
        let query = parse_query(&serde_json::json!({
            "match": {
                "message": "hello world"
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::Match {
                field: "message".to_string(),
                query: serde_json::json!("hello world")
            }
        );
    }

    #[test]
    fn parses_match_query_with_query_object() {
        let query = parse_query(&serde_json::json!({
            "match": {
                "message": {
                    "query": "hello world"
                }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::Match {
                field: "message".to_string(),
                query: serde_json::json!("hello world")
            }
        );
    }

    #[test]
    fn parses_range_query() {
        let query = parse_query(&serde_json::json!({
            "range": {
                "bytes": {
                    "gte": 100,
                    "lt": 200
                }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::Range {
                field: "bytes".to_string(),
                bounds: RangeBounds {
                    gt: None,
                    gte: Some(serde_json::json!(100)),
                    lt: Some(serde_json::json!(200)),
                    lte: None
                }
            }
        );
    }

    #[test]
    fn rejects_unsupported_range_options() {
        let error = parse_query(&serde_json::json!({
            "range": {
                "created_at": {
                    "time_zone": "UTC"
                }
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedOption {
                clause: "range".to_string(),
                option: "time_zone".to_string()
            }
        );
    }

    #[test]
    fn parses_bool_query_with_nested_clauses() {
        let query = parse_query(&serde_json::json!({
            "bool": {
                "must": [
                    {
                        "term": {
                            "service": "api"
                        }
                    }
                ],
                "filter": {
                    "range": {
                        "bytes": {
                            "gte": 100
                        }
                    }
                },
                "should": {
                    "match_all": {}
                },
                "must_not": [
                    {
                        "match": {
                            "message": "debug"
                        }
                    }
                ],
                "minimum_should_match": "1"
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::Bool {
                clauses: BoolQuery {
                    must: vec![Query::Term {
                        field: "service".to_string(),
                        value: serde_json::json!("api")
                    }],
                    should: vec![Query::MatchAll],
                    filter: vec![Query::Range {
                        field: "bytes".to_string(),
                        bounds: RangeBounds {
                            gt: None,
                            gte: Some(serde_json::json!(100)),
                            lt: None,
                            lte: None
                        }
                    }],
                    must_not: vec![Query::Match {
                        field: "message".to_string(),
                        query: serde_json::json!("debug")
                    }],
                    minimum_should_match: Some(1)
                }
            }
        );
    }

    #[test]
    fn rejects_unsupported_bool_options() {
        let error = parse_query(&serde_json::json!({
            "bool": {
                "boost": 2.0
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedOption {
                clause: "bool".to_string(),
                option: "boost".to_string()
            }
        );
    }

    #[test]
    fn parses_terms_aggregation_from_search_body() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "query": {
                "match_all": {}
            },
            "aggs": {
                "by_service": {
                    "terms": {
                        "field": "service",
                        "size": 5
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["by_service"],
            Aggregation::Terms(TermsAggregation {
                field: "service".to_string(),
                size: 5
            })
        );
    }

    #[test]
    fn parses_terms_aggregation_with_default_size() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggregations": {
                "by_level": {
                    "terms": {
                        "field": "level"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["by_level"],
            Aggregation::Terms(TermsAggregation {
                field: "level".to_string(),
                size: 10
            })
        );
    }

    #[test]
    fn parses_metric_aggregations() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "min_bytes": {
                    "min": {
                        "field": "bytes"
                    }
                },
                "avg_latency": {
                    "avg": {
                        "field": "latency"
                    }
                },
                "count_bytes": {
                    "value_count": {
                        "field": "bytes"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["min_bytes"],
            Aggregation::Metric(MetricAggregation {
                kind: MetricAggregationKind::Min,
                field: "bytes".to_string(),
            })
        );
        assert_eq!(
            aggregations["avg_latency"],
            Aggregation::Metric(MetricAggregation {
                kind: MetricAggregationKind::Avg,
                field: "latency".to_string(),
            })
        );
        assert_eq!(
            aggregations["count_bytes"],
            Aggregation::Metric(MetricAggregation {
                kind: MetricAggregationKind::ValueCount,
                field: "bytes".to_string(),
            })
        );
    }

    #[test]
    fn rejects_unsupported_metric_aggregation_options() {
        let error = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "sum_bytes": {
                    "sum": {
                        "field": "bytes",
                        "missing": 0
                    }
                }
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedOption {
                clause: "sum".to_string(),
                option: "missing".to_string()
            }
        );
    }

    #[test]
    fn parses_filter_and_filters_aggregations() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "only_errors": {
                    "filter": {
                        "term": {
                            "level": "error"
                        }
                    }
                },
                "by_level": {
                    "filters": {
                        "filters": {
                            "errors": {
                                "term": {
                                    "level": "error"
                                }
                            },
                            "infos": {
                                "term": {
                                    "level": "info"
                                }
                            }
                        }
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["only_errors"],
            Aggregation::Filter(FilterAggregation {
                filter: Query::Term {
                    field: "level".to_string(),
                    value: serde_json::json!("error"),
                }
            })
        );
        assert_eq!(
            aggregations["by_level"],
            Aggregation::Filters(FiltersAggregation {
                filters: BTreeMap::from([
                    (
                        "errors".to_string(),
                        Query::Term {
                            field: "level".to_string(),
                            value: serde_json::json!("error"),
                        },
                    ),
                    (
                        "infos".to_string(),
                        Query::Term {
                            field: "level".to_string(),
                            value: serde_json::json!("info"),
                        },
                    ),
                ])
            })
        );
    }

    #[test]
    fn rejects_unsupported_filters_aggregation_options() {
        let error = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "by_level": {
                    "filters": {
                        "filters": {
                            "errors": {
                                "term": {
                                    "level": "error"
                                }
                            }
                        },
                        "other_bucket": true
                    }
                }
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedOption {
                clause: "filters".to_string(),
                option: "other_bucket".to_string()
            }
        );
    }

    #[test]
    fn parses_top_hits_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "recent": {
                    "top_hits": {
                        "from": 1,
                        "size": 2
                    }
                },
                "default_recent": {
                    "top_hits": {}
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["recent"],
            Aggregation::TopHits(TopHitsAggregation { from: 1, size: 2 })
        );
        assert_eq!(
            aggregations["default_recent"],
            Aggregation::TopHits(TopHitsAggregation { from: 0, size: 3 })
        );
    }

    #[test]
    fn rejects_unsupported_top_hits_aggregation_options() {
        let error = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "recent": {
                    "top_hits": {
                        "sort": [
                            {
                                "timestamp": "desc"
                            }
                        ]
                    }
                }
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedOption {
                clause: "top_hits".to_string(),
                option: "sort".to_string()
            }
        );
    }

    #[test]
    fn parses_composite_terms_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "by_service_level": {
                    "composite": {
                        "size": 5,
                        "sources": [
                            {
                                "service": {
                                    "terms": {
                                        "field": "service"
                                    }
                                }
                            },
                            {
                                "level": {
                                    "terms": {
                                        "field": "level"
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["by_service_level"],
            Aggregation::Composite(CompositeAggregation {
                size: 5,
                sources: vec![
                    CompositeTermsSource {
                        name: "service".to_string(),
                        field: "service".to_string(),
                    },
                    CompositeTermsSource {
                        name: "level".to_string(),
                        field: "level".to_string(),
                    },
                ],
            })
        );
    }

    #[test]
    fn rejects_unsupported_composite_source_options() {
        let error = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "by_service": {
                    "composite": {
                        "sources": [
                            {
                                "service": {
                                    "terms": {
                                        "field": "service",
                                        "missing_bucket": true
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedOption {
                clause: "composite.terms".to_string(),
                option: "missing_bucket".to_string()
            }
        );
    }

    #[test]
    fn parses_significant_terms_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "interesting_tags": {
                    "significant_terms": {
                        "field": "tags",
                        "size": 4
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["interesting_tags"],
            Aggregation::SignificantTerms(SignificantTermsAggregation {
                field: "tags".to_string(),
                size: 4
            })
        );
    }

    #[test]
    fn rejects_unsupported_significant_terms_options() {
        let error = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "interesting_tags": {
                    "significant_terms": {
                        "field": "tags",
                        "background_filter": {
                            "match_all": {}
                        }
                    }
                }
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedOption {
                clause: "significant_terms".to_string(),
                option: "background_filter".to_string()
            }
        );
    }

    #[test]
    fn parses_geo_bounds_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "viewport": {
                    "geo_bounds": {
                        "field": "location"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["viewport"],
            Aggregation::GeoBounds(GeoBoundsAggregation {
                field: "location".to_string()
            })
        );
    }

    #[test]
    fn rejects_unsupported_geo_bounds_options() {
        let error = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "viewport": {
                    "geo_bounds": {
                        "field": "location",
                        "wrap_longitude": true
                    }
                }
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedOption {
                clause: "geo_bounds".to_string(),
                option: "wrap_longitude".to_string()
            }
        );
    }

    #[test]
    fn parses_sum_bucket_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "total_services": {
                    "sum_bucket": {
                        "buckets_path": "by_service>_count"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["total_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::SumBucket,
                buckets_path: "by_service>_count".to_string()
            })
        );
    }

    #[test]
    fn rejects_unsupported_sum_bucket_options() {
        let error = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "total_services": {
                    "sum_bucket": {
                        "buckets_path": "by_service>_count",
                        "gap_policy": "insert_zeros"
                    }
                }
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedOption {
                clause: "sum_bucket".to_string(),
                option: "gap_policy".to_string()
            }
        );
    }

    #[test]
    fn parses_scripted_metric_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "custom_metric": {
                    "scripted_metric": {
                        "init_script": "state.values = []",
                        "map_script": "state.values.add(doc['bytes'].value)",
                        "combine_script": "return params.value",
                        "reduce_script": "return states[0]",
                        "params": {
                            "value": 42
                        }
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["custom_metric"],
            Aggregation::ScriptedMetric(ScriptedMetricAggregation {
                value: Some(serde_json::json!(42))
            })
        );
    }

    #[test]
    fn rejects_unsupported_scripted_metric_options() {
        let error = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "custom_metric": {
                    "scripted_metric": {
                        "map_script": "return 1",
                        "field": "bytes"
                    }
                }
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedOption {
                clause: "scripted_metric".to_string(),
                option: "field".to_string()
            }
        );
    }

    #[test]
    fn parses_plugin_aggregation_wrapper() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "custom": {
                    "plugin": {
                        "name": "example-plugin",
                        "kind": "example_metric",
                        "params": {
                            "field": "bytes"
                        }
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["custom"],
            Aggregation::Plugin(PluginAggregation {
                name: "example-plugin".to_string(),
                kind: "example_metric".to_string(),
                params: serde_json::json!({
                    "field": "bytes"
                })
            })
        );
    }

    #[test]
    fn rejects_unsupported_plugin_aggregation_options() {
        let error = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "custom": {
                    "plugin": {
                        "name": "example-plugin",
                        "kind": "example_metric",
                        "extra": true
                    }
                }
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedOption {
                clause: "plugin".to_string(),
                option: "extra".to_string()
            }
        );
    }

    #[test]
    fn rejects_unsupported_terms_aggregation_options() {
        let error = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "by_service": {
                    "terms": {
                        "field": "service",
                        "order": {
                            "_key": "asc"
                        }
                    }
                }
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedOption {
                clause: "terms".to_string(),
                option: "order".to_string()
            }
        );
    }

    #[test]
    fn aggregation_response_models_terms_buckets() {
        let mut aggregations = BTreeMap::new();
        aggregations.insert(
            "by_service".to_string(),
            AggregationResult::Terms(TermsAggregationResult {
                buckets: vec![TermsBucket {
                    key: serde_json::json!("api"),
                    doc_count: 3,
                }],
            }),
        );

        let response = AggregationResponse { aggregations };

        assert_eq!(
            response.aggregations["by_service"],
            AggregationResult::Terms(TermsAggregationResult {
                buckets: vec![TermsBucket {
                    key: serde_json::json!("api"),
                    doc_count: 3
                }]
            })
        );
    }

    #[test]
    fn parses_search_aggregations_from_aggregations_alias() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggregations": {
                "latency_sum": {
                    "sum": {
                        "field": "latency_ms"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["latency_sum"],
            Aggregation::Metric(MetricAggregation {
                kind: MetricAggregationKind::Sum,
                field: "latency_ms".to_string(),
            })
        );
    }

    #[test]
    fn rejects_metric_aggregation_with_unsupported_option() {
        let error = parse_aggregation_map(&serde_json::json!({
            "latency_sum": {
                "sum": {
                    "field": "latency_ms",
                    "missing": 0
                }
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedOption {
                clause: "sum".to_string(),
                option: "missing".to_string()
            }
        );
    }

    #[test]
    fn rejects_unsupported_query_clause() {
        let error = parse_query(&serde_json::json!({
            "geo_shape": {}
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedClause {
                clause: "geo_shape".to_string()
            }
        );
    }
}
