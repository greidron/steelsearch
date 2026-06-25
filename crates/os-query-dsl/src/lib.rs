//! OpenSearch query DSL model placeholders.

use base64::engine::general_purpose::STANDARD;
use base64::Engine;
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
    SpanTerm {
        field: String,
        value: serde_json::Value,
    },
    SpanGap {
        field: String,
        width: usize,
    },
    SpanOr {
        clauses: Vec<Query>,
    },
    SpanFirst {
        match_query: Box<Query>,
        end: usize,
    },
    SpanNear {
        clauses: Vec<Query>,
        slop: usize,
        in_order: bool,
    },
    SpanNot {
        include: Box<Query>,
        exclude: Box<Query>,
    },
    SpanContaining {
        big: Box<Query>,
        little: Box<Query>,
    },
    SpanWithin {
        big: Box<Query>,
        little: Box<Query>,
    },
    SpanMulti {
        query: Box<Query>,
    },
    FieldMaskingSpan {
        query: Box<Query>,
        field: String,
    },
    TermsSet {
        field: String,
        values: Vec<serde_json::Value>,
        minimum_should_match: usize,
    },
    Match {
        field: String,
        query: serde_json::Value,
    },
    MatchPhrase {
        field: String,
        query: serde_json::Value,
    },
    MatchPhrasePrefix {
        field: String,
        query: serde_json::Value,
    },
    MatchBoolPrefix {
        field: String,
        query: serde_json::Value,
    },
    CombinedFields {
        query: String,
        fields: Vec<String>,
    },
    MultiMatch {
        fields: Vec<String>,
        query: serde_json::Value,
    },
    QueryString {
        query: String,
        fields: Option<Vec<String>>,
    },
    SimpleQueryString {
        query: String,
        fields: Option<Vec<String>>,
    },
    MoreLikeThis {
        fields: Option<Vec<String>>,
        like: Vec<String>,
    },
    Range {
        field: String,
        bounds: RangeBounds,
    },
    GeoDistance(GeoDistanceQuery),
    GeoBoundingBox(GeoBoundingBoxQuery),
    GeoPolygon(GeoPolygonQuery),
    GeoShape(GeoShapeQuery),
    Exists {
        field: String,
    },
    DistanceFeature {
        field: String,
        origin: Value,
        pivot: Value,
    },
    RankFeature {
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
    Regexp {
        field: String,
        value: String,
        case_insensitive: bool,
    },
    Fuzzy {
        field: String,
        value: String,
        fuzziness: u8,
        prefix_length: usize,
        transpositions: bool,
    },
    Wrapper {
        query: Box<Query>,
    },
    Nested {
        path: String,
        query: Box<Query>,
    },
    Pinned {
        ids: Vec<String>,
        organic: Box<Query>,
    },
    ConstantScore {
        filter: Box<Query>,
    },
    DisMax {
        queries: Vec<Query>,
        tie_breaker: Option<f64>,
    },
    Boosting {
        positive: Box<Query>,
        negative: Box<Query>,
        negative_boost: f64,
    },
    FunctionScore {
        query: Box<Query>,
    },
    ScriptScore {
        query: Box<Query>,
        script: Value,
    },
    Script {
        script: Value,
    },
    Intervals {
        field: String,
        spec: Value,
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

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct GeoDistanceQuery {
    pub field: String,
    pub distance_meters: f64,
    pub lat: f64,
    pub lon: f64,
    pub ignore_unmapped: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct GeoBoundingBoxQuery {
    pub field: String,
    pub top: f64,
    pub left: f64,
    pub bottom: f64,
    pub right: f64,
    pub ignore_unmapped: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct GeoPolygonQuery {
    pub field: String,
    pub points: Vec<GeoPoint>,
    pub ignore_unmapped: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct GeoShapeQuery {
    pub field: String,
    pub shape: Value,
    pub relation: String,
    pub ignore_unmapped: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct GeoPoint {
    pub lat: f64,
    pub lon: f64,
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
    DateHistogram(DateHistogramAggregation),
    Histogram(HistogramAggregation),
    Range(RangeAggregation),
    Metric(MetricAggregation),
    Missing(MissingAggregation),
    Filter(FilterAggregation),
    Filters(FiltersAggregation),
    TopHits(TopHitsAggregation),
    Composite(CompositeAggregation),
    SignificantTerms(SignificantTermsAggregation),
    GeoBounds(GeoBoundsAggregation),
    GeoCentroid(GeoCentroidAggregation),
    BucketSort(BucketSortAggregation),
    BucketCount(BucketCountAggregation),
    Normalize(NormalizeAggregation),
    BucketSelector(BucketSelectorAggregation),
    BucketScript(BucketScriptAggregation),
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
pub struct DateHistogramAggregation {
    pub field: String,
    pub interval: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct HistogramAggregation {
    pub field: String,
    pub interval: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct RangeAggregation {
    pub field: String,
    pub ranges: Vec<RangeBucket>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct RangeBucket {
    pub key: Option<String>,
    pub from: Option<f64>,
    pub to: Option<f64>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MetricAggregationKind {
    Min,
    Max,
    Sum,
    Avg,
    WeightedAvg,
    Boxplot,
    Stats,
    ExtendedStats,
    Percentiles,
    PercentileRanks,
    MedianAbsoluteDeviation,
    Cardinality,
    ValueCount,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct MetricAggregation {
    pub kind: MetricAggregationKind,
    pub field: String,
    pub weight_field: Option<String>,
    pub values: Option<Vec<f64>>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MissingAggregation {
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
pub struct GeoCentroidAggregation {
    pub field: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BucketSortAggregation {
    pub aggregation: String,
    pub sort: Vec<Value>,
    pub from: usize,
    pub size: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct BucketCountAggregation {
    pub aggregation: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct NormalizeAggregation {
    pub aggregation: String,
    pub path: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BucketSelectorAggregation {
    pub aggregation: String,
    pub path: String,
    pub op: String,
    pub value: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BucketScriptAggregation {
    pub aggregation: String,
    pub path: String,
    pub script: String,
    pub params: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct PipelineAggregation {
    pub kind: PipelineAggregationKind,
    pub buckets_path: String,
    pub window: Option<usize>,
    pub percents: Option<Vec<f64>>,
    pub values: Option<Vec<f64>>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PipelineAggregationKind {
    SumBucket,
    AvgBucket,
    MinBucket,
    MaxBucket,
    MovingCount,
    MovingAvg,
    MovingSum,
    MovingMin,
    MovingMax,
    MovingMedian,
    MovingMad,
    MovingStddev,
    MovingVariance,
    MovingSkewness,
    MovingKurtosis,
    MovingRange,
    MovingPercentiles,
    MovingPercentileRanks,
    CumulativeSum,
    SerialDiff,
    Derivative,
    StatsBucket,
    ExtendedStatsBucket,
    PercentilesBucket,
    PercentileRanksBucket,
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
    DateHistogram(DateHistogramAggregationResult),
    Histogram(HistogramAggregationResult),
    Range(RangeAggregationResult),
    Metric(MetricAggregationResult),
    Missing(MissingAggregationResult),
    Filter(FilterAggregationResult),
    Filters(FiltersAggregationResult),
    TopHits(TopHitsAggregationResult),
    Composite(CompositeAggregationResult),
    SignificantTerms(SignificantTermsAggregationResult),
    GeoBounds(GeoBoundsAggregationResult),
    GeoCentroid(GeoCentroidAggregationResult),
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
pub struct DateHistogramAggregationResult {
    pub buckets: Vec<DateHistogramBucket>,
}

#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct HistogramAggregationResult {
    pub buckets: Vec<HistogramBucket>,
}

#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct HistogramBucket {
    pub key: f64,
    pub doc_count: u64,
}

#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct RangeAggregationResult {
    pub buckets: Vec<RangeBucketResult>,
}

#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct RangeBucketResult {
    pub key: Option<String>,
    pub from: Option<f64>,
    pub to: Option<f64>,
    pub doc_count: u64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct DateHistogramBucket {
    pub key: i64,
    pub key_as_string: String,
    pub doc_count: u64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct MetricAggregationResult {
    pub value: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct MissingAggregationResult {
    pub doc_count: u64,
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
pub struct GeoCentroidAggregationResult {
    pub location: Value,
    pub count: u64,
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
        "span_term" => parse_span_term(body),
        "span_gap" => parse_span_gap(body),
        "span_or" => parse_span_or(body),
        "span_first" => parse_span_first(body),
        "span_near" => parse_span_near(body),
        "span_not" => parse_span_not(body),
        "span_containing" => parse_span_containing(body),
        "span_within" => parse_span_within(body),
        "span_multi" => parse_span_multi(body),
        "field_masking_span" => parse_field_masking_span(body),
        "terms_set" => parse_terms_set(body),
        "match" => parse_match(body),
        "match_phrase" => parse_match_phrase(body),
        "match_phrase_prefix" => parse_match_phrase_prefix(body),
        "match_bool_prefix" => parse_match_bool_prefix(body),
        "combined_fields" => parse_combined_fields(body),
        "multi_match" => parse_multi_match(body),
        "query_string" => parse_query_string(body),
        "simple_query_string" => parse_simple_query_string(body),
        "more_like_this" => parse_more_like_this(body),
        "range" => parse_range(body),
        "geo_distance" => parse_geo_distance(body),
        "geo_bounding_box" => parse_geo_bounding_box(body),
        "geo_polygon" => parse_geo_polygon(body),
        "geo_shape" => parse_geo_shape(body),
        "exists" => parse_exists(body),
        "distance_feature" => parse_distance_feature(body),
        "rank_feature" => parse_rank_feature(body),
        "ids" => parse_ids(body),
        "prefix" => parse_prefix(body),
        "wildcard" => parse_wildcard(body),
        "regexp" => parse_regexp(body),
        "fuzzy" => parse_fuzzy(body),
        "wrapper" => parse_wrapper(body),
        "nested" => parse_nested(body),
        "pinned" => parse_pinned(body),
        "constant_score" => parse_constant_score(body),
        "dis_max" => parse_dis_max(body),
        "boosting" => parse_boosting(body),
        "function_score" => parse_function_score(body),
        "script_score" => parse_script_score(body),
        "script" => parse_script(body),
        "intervals" => parse_intervals(body),
        "template" => parse_template(body),
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
        "date_histogram" => parse_date_histogram_aggregation(body),
        "histogram" => parse_histogram_aggregation(body),
        "range" => parse_range_aggregation(body),
        "min" => parse_metric_aggregation(MetricAggregationKind::Min, kind, body),
        "max" => parse_metric_aggregation(MetricAggregationKind::Max, kind, body),
        "sum" => parse_metric_aggregation(MetricAggregationKind::Sum, kind, body),
        "avg" => parse_metric_aggregation(MetricAggregationKind::Avg, kind, body),
        "weighted_avg" => parse_metric_aggregation(MetricAggregationKind::WeightedAvg, kind, body),
        "boxplot" => parse_metric_aggregation(MetricAggregationKind::Boxplot, kind, body),
        "stats" => parse_metric_aggregation(MetricAggregationKind::Stats, kind, body),
        "extended_stats" => {
            parse_metric_aggregation(MetricAggregationKind::ExtendedStats, kind, body)
        }
        "percentiles" => parse_metric_aggregation(MetricAggregationKind::Percentiles, kind, body),
        "percentile_ranks" => {
            parse_metric_aggregation(MetricAggregationKind::PercentileRanks, kind, body)
        }
        "median_absolute_deviation" => {
            parse_metric_aggregation(MetricAggregationKind::MedianAbsoluteDeviation, kind, body)
        }
        "cardinality" => parse_metric_aggregation(MetricAggregationKind::Cardinality, kind, body),
        "value_count" => parse_metric_aggregation(MetricAggregationKind::ValueCount, kind, body),
        "missing" => parse_missing_aggregation(body),
        "filter" => parse_filter_aggregation(body),
        "filters" => parse_filters_aggregation(body),
        "top_hits" => parse_top_hits_aggregation(body),
        "composite" => parse_composite_aggregation(body),
        "significant_terms" => parse_significant_terms_aggregation(body),
        "geo_bounds" => parse_geo_bounds_aggregation(body),
        "geo_centroid" => parse_geo_centroid_aggregation(body),
        "bucket_sort" => parse_bucket_sort_aggregation(body),
        "bucket_count" => parse_bucket_count_aggregation(body),
        "normalize" => parse_normalize_aggregation(body),
        "bucket_selector" => parse_bucket_selector_aggregation(body),
        "bucket_script" => parse_bucket_script_aggregation(body),
        "sum_bucket" => parse_pipeline_aggregation(PipelineAggregationKind::SumBucket, kind, body),
        "avg_bucket" => parse_pipeline_aggregation(PipelineAggregationKind::AvgBucket, kind, body),
        "min_bucket" => parse_pipeline_aggregation(PipelineAggregationKind::MinBucket, kind, body),
        "max_bucket" => parse_pipeline_aggregation(PipelineAggregationKind::MaxBucket, kind, body),
        "moving_count" => {
            parse_pipeline_aggregation(PipelineAggregationKind::MovingCount, kind, body)
        }
        "moving_avg" => parse_pipeline_aggregation(PipelineAggregationKind::MovingAvg, kind, body),
        "moving_sum" => parse_pipeline_aggregation(PipelineAggregationKind::MovingSum, kind, body),
        "moving_min" => parse_pipeline_aggregation(PipelineAggregationKind::MovingMin, kind, body),
        "moving_max" => parse_pipeline_aggregation(PipelineAggregationKind::MovingMax, kind, body),
        "moving_median" => {
            parse_pipeline_aggregation(PipelineAggregationKind::MovingMedian, kind, body)
        }
        "moving_mad" => parse_pipeline_aggregation(PipelineAggregationKind::MovingMad, kind, body),
        "moving_stddev" => {
            parse_pipeline_aggregation(PipelineAggregationKind::MovingStddev, kind, body)
        }
        "moving_variance" => {
            parse_pipeline_aggregation(PipelineAggregationKind::MovingVariance, kind, body)
        }
        "moving_skewness" => {
            parse_pipeline_aggregation(PipelineAggregationKind::MovingSkewness, kind, body)
        }
        "moving_kurtosis" => {
            parse_pipeline_aggregation(PipelineAggregationKind::MovingKurtosis, kind, body)
        }
        "moving_range" => {
            parse_pipeline_aggregation(PipelineAggregationKind::MovingRange, kind, body)
        }
        "moving_percentiles" => {
            parse_pipeline_aggregation(PipelineAggregationKind::MovingPercentiles, kind, body)
        }
        "moving_percentile_ranks" => {
            parse_pipeline_aggregation(PipelineAggregationKind::MovingPercentileRanks, kind, body)
        }
        "cumulative_sum" => {
            parse_pipeline_aggregation(PipelineAggregationKind::CumulativeSum, kind, body)
        }
        "serial_diff" => {
            parse_pipeline_aggregation(PipelineAggregationKind::SerialDiff, kind, body)
        }
        "derivative" => parse_pipeline_aggregation(PipelineAggregationKind::Derivative, kind, body),
        "stats_bucket" => {
            parse_pipeline_aggregation(PipelineAggregationKind::StatsBucket, kind, body)
        }
        "extended_stats_bucket" => {
            parse_pipeline_aggregation(PipelineAggregationKind::ExtendedStatsBucket, kind, body)
        }
        "percentiles_bucket" => {
            parse_pipeline_aggregation(PipelineAggregationKind::PercentilesBucket, kind, body)
        }
        "percentile_ranks_bucket" => {
            parse_pipeline_aggregation(PipelineAggregationKind::PercentileRanksBucket, kind, body)
        }
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

fn parse_date_histogram_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let field = object
        .get("field")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "date_histogram".to_string(),
            field: "field".to_string(),
        })?
        .to_string();
    let interval = object
        .get("calendar_interval")
        .or_else(|| object.get("fixed_interval"))
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "date_histogram".to_string(),
            field: "calendar_interval".to_string(),
        })?
        .to_string();

    for option in object.keys() {
        match option.as_str() {
            "field" | "calendar_interval" | "fixed_interval" => {}
            _ => {
                return Err(QueryDslError::UnsupportedOption {
                    clause: "date_histogram".to_string(),
                    option: option.clone(),
                });
            }
        }
    }

    Ok(Aggregation::DateHistogram(DateHistogramAggregation {
        field,
        interval,
    }))
}

fn parse_range_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let field = object
        .get("field")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "range".to_string(),
            field: "field".to_string(),
        })?
        .to_string();
    let ranges = object
        .get("ranges")
        .and_then(Value::as_array)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "range".to_string(),
            field: "ranges".to_string(),
        })?;

    for option in object.keys() {
        match option.as_str() {
            "field" | "ranges" => {}
            _ => {
                return Err(QueryDslError::UnsupportedOption {
                    clause: "range".to_string(),
                    option: option.clone(),
                });
            }
        }
    }

    let parsed_ranges = ranges
        .iter()
        .map(|entry| {
            let object = entry.as_object().ok_or(QueryDslError::ExpectedObject)?;
            let key = object
                .get("key")
                .and_then(Value::as_str)
                .map(ToString::to_string);
            let from = object.get("from").and_then(Value::as_f64);
            let to = object.get("to").and_then(Value::as_f64);
            if from.is_none() && to.is_none() {
                return Err(QueryDslError::MissingField {
                    clause: "range".to_string(),
                    field: "from|to".to_string(),
                });
            }
            for option in object.keys() {
                match option.as_str() {
                    "key" | "from" | "to" => {}
                    _ => {
                        return Err(QueryDslError::UnsupportedOption {
                            clause: "range".to_string(),
                            option: option.clone(),
                        });
                    }
                }
            }
            Ok(RangeBucket { key, from, to })
        })
        .collect::<QueryDslResult<Vec<_>>>()?;

    Ok(Aggregation::Range(RangeAggregation {
        field,
        ranges: parsed_ranges,
    }))
}

fn parse_histogram_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let field = object
        .get("field")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "histogram".to_string(),
            field: "field".to_string(),
        })?
        .to_string();
    let interval = object
        .get("interval")
        .and_then(Value::as_f64)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "histogram".to_string(),
            field: "interval".to_string(),
        })?;
    for option in object.keys() {
        match option.as_str() {
            "field" | "interval" => {}
            _ => {
                return Err(QueryDslError::UnsupportedOption {
                    clause: "histogram".to_string(),
                    option: option.clone(),
                });
            }
        }
    }
    Ok(Aggregation::Histogram(HistogramAggregation {
        field,
        interval,
    }))
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
    let weight_field = object
        .get("weight_field")
        .and_then(Value::as_str)
        .map(ToString::to_string);
    let values = object.get("values").map(parse_numeric_array).transpose()?;

    for option in object.keys() {
        let allowed_weight_field =
            matches!(kind, MetricAggregationKind::WeightedAvg) && option == "weight_field";
        let allowed_values =
            matches!(kind, MetricAggregationKind::PercentileRanks) && option == "values";
        if option != "field" && !allowed_weight_field && !allowed_values {
            return Err(QueryDslError::UnsupportedOption {
                clause: clause.to_string(),
                option: option.clone(),
            });
        }
    }

    if matches!(kind, MetricAggregationKind::WeightedAvg) && weight_field.is_none() {
        return Err(QueryDslError::MissingField {
            clause: clause.to_string(),
            field: "weight_field".to_string(),
        });
    }

    if matches!(kind, MetricAggregationKind::PercentileRanks) && values.is_none() {
        return Err(QueryDslError::MissingField {
            clause: clause.to_string(),
            field: "values".to_string(),
        });
    }

    Ok(Aggregation::Metric(MetricAggregation {
        kind,
        field,
        weight_field,
        values,
    }))
}

fn parse_numeric_array(value: &Value) -> QueryDslResult<Vec<f64>> {
    let array = value
        .as_array()
        .ok_or_else(|| QueryDslError::ExpectedArray {
            clause: "percentile_ranks".to_string(),
            field: "values".to_string(),
        })?;
    array
        .iter()
        .map(|value| {
            value.as_f64().ok_or_else(|| QueryDslError::InvalidValue {
                clause: "percentile_ranks".to_string(),
                field: "values".to_string(),
                reason: "must contain only numeric values".to_string(),
            })
        })
        .collect()
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

fn parse_geo_centroid_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let field = object
        .get("field")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "geo_centroid".to_string(),
            field: "field".to_string(),
        })?
        .to_string();

    for option in object.keys() {
        if option != "field" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "geo_centroid".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Aggregation::GeoCentroid(GeoCentroidAggregation { field }))
}

fn parse_bucket_sort_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let aggregation = object
        .get("aggregation")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "bucket_sort".to_string(),
            field: "aggregation".to_string(),
        })?
        .to_string();
    let sort = object
        .get("sort")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    let from = object
        .get("from")
        .and_then(Value::as_u64)
        .and_then(|value| usize::try_from(value).ok())
        .unwrap_or(0);
    let size = object
        .get("size")
        .and_then(Value::as_u64)
        .and_then(|value| usize::try_from(value).ok())
        .unwrap_or(10);

    for option in object.keys() {
        if option != "aggregation" && option != "sort" && option != "from" && option != "size" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "bucket_sort".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Aggregation::BucketSort(BucketSortAggregation {
        aggregation,
        sort,
        from,
        size,
    }))
}

fn parse_bucket_script_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let aggregation = object
        .get("aggregation")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "bucket_script".to_string(),
            field: "aggregation".to_string(),
        })?
        .to_string();
    let path = object
        .get("path")
        .and_then(Value::as_str)
        .unwrap_or("_count")
        .to_string();
    let script = object
        .get("script")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "bucket_script".to_string(),
            field: "script".to_string(),
        })?
        .to_string();
    let params = object
        .get("params")
        .and_then(Value::as_object)
        .cloned()
        .unwrap_or_default()
        .into_iter()
        .collect::<BTreeMap<_, _>>();

    for option in object.keys() {
        if option != "aggregation" && option != "path" && option != "script" && option != "params" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "bucket_script".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Aggregation::BucketScript(BucketScriptAggregation {
        aggregation,
        path,
        script,
        params,
    }))
}

fn parse_bucket_selector_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let aggregation = object
        .get("aggregation")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "bucket_selector".to_string(),
            field: "aggregation".to_string(),
        })?
        .to_string();
    let path = object
        .get("path")
        .and_then(Value::as_str)
        .unwrap_or("_count")
        .to_string();
    let op = object
        .get("op")
        .and_then(Value::as_str)
        .unwrap_or("gte")
        .to_string();
    let value =
        object
            .get("value")
            .and_then(Value::as_f64)
            .ok_or_else(|| QueryDslError::MissingField {
                clause: "bucket_selector".to_string(),
                field: "value".to_string(),
            })?;

    for option in object.keys() {
        if option != "aggregation" && option != "path" && option != "op" && option != "value" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "bucket_selector".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Aggregation::BucketSelector(BucketSelectorAggregation {
        aggregation,
        path,
        op,
        value,
    }))
}

fn parse_bucket_count_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let aggregation = object
        .get("aggregation")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "bucket_count".to_string(),
            field: "aggregation".to_string(),
        })?
        .to_string();

    for option in object.keys() {
        if option != "aggregation" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "bucket_count".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Aggregation::BucketCount(BucketCountAggregation {
        aggregation,
    }))
}

fn parse_normalize_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let aggregation = object
        .get("aggregation")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "normalize".to_string(),
            field: "aggregation".to_string(),
        })?
        .to_string();
    let path = object
        .get("path")
        .and_then(Value::as_str)
        .unwrap_or("_count")
        .to_string();

    for option in object.keys() {
        if option != "aggregation" && option != "path" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "normalize".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Aggregation::Normalize(NormalizeAggregation {
        aggregation,
        path,
    }))
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
    let window = object
        .get("window")
        .and_then(Value::as_u64)
        .map(|value| value as usize);
    let lag = object
        .get("lag")
        .and_then(Value::as_u64)
        .map(|value| value as usize);
    let percents = object
        .get("percents")
        .and_then(Value::as_array)
        .map(|values| values.iter().filter_map(Value::as_f64).collect::<Vec<_>>());
    let values = object
        .get("values")
        .and_then(Value::as_array)
        .map(|values| values.iter().filter_map(Value::as_f64).collect::<Vec<_>>());

    for option in object.keys() {
        if option != "buckets_path"
            && option != "window"
            && option != "lag"
            && option != "percents"
            && option != "values"
        {
            return Err(QueryDslError::UnsupportedOption {
                clause: clause.to_string(),
                option: option.clone(),
            });
        }
    }

    let is_serial_diff = matches!(kind, PipelineAggregationKind::SerialDiff);

    if lag.is_some() && !is_serial_diff {
        return Err(QueryDslError::UnsupportedOption {
            clause: clause.to_string(),
            option: "lag".to_string(),
        });
    }

    Ok(Aggregation::Pipeline(PipelineAggregation {
        kind,
        buckets_path,
        window: if is_serial_diff {
            window.or(lag)
        } else {
            window
        },
        percents,
        values,
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

fn parse_missing_aggregation(body: &Value) -> QueryDslResult<Aggregation> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let field = object
        .get("field")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "missing".to_string(),
            field: "field".to_string(),
        })?
        .to_string();
    for option in object.keys() {
        if option != "field" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "missing".to_string(),
                option: option.clone(),
            });
        }
    }
    Ok(Aggregation::Missing(MissingAggregation { field }))
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
            "sort" => {
                if !value.is_array() && !value.is_object() {
                    return Err(QueryDslError::InvalidValue {
                        clause: "top_hits".to_string(),
                        field: "sort".to_string(),
                        reason: "expected object or array".to_string(),
                    });
                }
            }
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
        if let Some(value) = object.get("value") {
            value.clone()
        } else if object.contains_key("boost") || object.contains_key("case_insensitive") {
            return Err(QueryDslError::MissingField {
                clause: "term".to_string(),
                field: "value".to_string(),
            });
        } else {
            term_body.clone()
        }
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

fn parse_span_term(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if object.len() != 1 {
        return Err(QueryDslError::ExpectedSingleField {
            clause: "span_term".to_string(),
        });
    }

    let (field, value) = object.iter().next().expect("checked len");
    Ok(Query::SpanTerm {
        field: field.clone(),
        value: value.clone(),
    })
}

fn parse_span_gap(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if object.len() != 1 {
        return Err(QueryDslError::ExpectedSingleField {
            clause: "span_gap".to_string(),
        });
    }

    let (field, value) = object.iter().next().expect("checked len");
    let width = value.as_u64().ok_or_else(|| QueryDslError::InvalidValue {
        clause: "span_gap".to_string(),
        field: field.clone(),
        reason: "width must be a non-negative integer".to_string(),
    })? as usize;
    Ok(Query::SpanGap {
        field: field.clone(),
        width,
    })
}

fn parse_span_or(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let clauses = object
        .get("clauses")
        .and_then(Value::as_array)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "span_or".to_string(),
            field: "clauses".to_string(),
        })?
        .iter()
        .map(parse_query)
        .collect::<QueryDslResult<Vec<_>>>()?;

    for option in object.keys() {
        if option != "clauses" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "span_or".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::SpanOr { clauses })
}

fn parse_span_first(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let match_query = object
        .get("match")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "span_first".to_string(),
            field: "match".to_string(),
        })
        .and_then(parse_query)?;
    let end =
        object
            .get("end")
            .and_then(Value::as_u64)
            .ok_or_else(|| QueryDslError::MissingField {
                clause: "span_first".to_string(),
                field: "end".to_string(),
            })? as usize;

    for option in object.keys() {
        if option != "match" && option != "end" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "span_first".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::SpanFirst {
        match_query: Box::new(match_query),
        end,
    })
}

fn parse_span_near(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let clauses = object
        .get("clauses")
        .and_then(Value::as_array)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "span_near".to_string(),
            field: "clauses".to_string(),
        })?
        .iter()
        .map(parse_query)
        .collect::<QueryDslResult<Vec<_>>>()?;
    let slop =
        object
            .get("slop")
            .and_then(Value::as_u64)
            .ok_or_else(|| QueryDslError::MissingField {
                clause: "span_near".to_string(),
                field: "slop".to_string(),
            })? as usize;
    let in_order = object
        .get("in_order")
        .and_then(Value::as_bool)
        .unwrap_or(true);

    for option in object.keys() {
        if option != "clauses" && option != "slop" && option != "in_order" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "span_near".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::SpanNear {
        clauses,
        slop,
        in_order,
    })
}

fn parse_span_not(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let include = object
        .get("include")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "span_not".to_string(),
            field: "include".to_string(),
        })
        .and_then(parse_query)?;
    let exclude = object
        .get("exclude")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "span_not".to_string(),
            field: "exclude".to_string(),
        })
        .and_then(parse_query)?;

    for option in object.keys() {
        if option != "include" && option != "exclude" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "span_not".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::SpanNot {
        include: Box::new(include),
        exclude: Box::new(exclude),
    })
}

fn parse_span_containing(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let big = object
        .get("big")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "span_containing".to_string(),
            field: "big".to_string(),
        })
        .and_then(parse_query)?;
    let little = object
        .get("little")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "span_containing".to_string(),
            field: "little".to_string(),
        })
        .and_then(parse_query)?;

    for option in object.keys() {
        if option != "big" && option != "little" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "span_containing".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::SpanContaining {
        big: Box::new(big),
        little: Box::new(little),
    })
}

fn parse_span_within(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let big = object
        .get("big")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "span_within".to_string(),
            field: "big".to_string(),
        })
        .and_then(parse_query)?;
    let little = object
        .get("little")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "span_within".to_string(),
            field: "little".to_string(),
        })
        .and_then(parse_query)?;

    for option in object.keys() {
        if option != "big" && option != "little" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "span_within".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::SpanWithin {
        big: Box::new(big),
        little: Box::new(little),
    })
}

fn parse_span_multi(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let query = object
        .get("match")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "span_multi".to_string(),
            field: "match".to_string(),
        })
        .and_then(parse_query)?;

    for option in object.keys() {
        if option != "match" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "span_multi".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::SpanMulti {
        query: Box::new(query),
    })
}

fn parse_field_masking_span(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let query = object
        .get("query")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "field_masking_span".to_string(),
            field: "query".to_string(),
        })
        .and_then(parse_query)?;
    let field = object
        .get("field")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "field_masking_span".to_string(),
            field: "field".to_string(),
        })?
        .to_string();

    for option in object.keys() {
        if option != "query" && option != "field" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "field_masking_span".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::FieldMaskingSpan {
        query: Box::new(query),
        field,
    })
}

fn parse_terms_set(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if object.len() != 1 {
        return Err(QueryDslError::ExpectedSingleField {
            clause: "terms_set".to_string(),
        });
    }

    let (field, field_body) = object.iter().next().expect("checked len");
    let field_object = field_body
        .as_object()
        .ok_or(QueryDslError::ExpectedObject)?;
    let values = field_object
        .get("terms")
        .and_then(Value::as_array)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "terms_set".to_string(),
            field: "terms".to_string(),
        })?
        .clone();
    let minimum_should_match = match field_object
        .get("minimum_should_match")
        .and_then(Value::as_u64)
    {
        Some(value) => value,
        None => field_object
            .get("minimum_should_match_script")
            .and_then(Value::as_object)
            .and_then(|script| script.get("source"))
            .and_then(|source| {
                source
                    .as_u64()
                    .or_else(|| source.as_str().and_then(|value| value.parse::<u64>().ok()))
            })
            .ok_or_else(|| QueryDslError::MissingField {
                clause: "terms_set".to_string(),
                field: "minimum_should_match".to_string(),
            })?,
    };
    let minimum_should_match =
        usize::try_from(minimum_should_match).map_err(|_| QueryDslError::InvalidValue {
            clause: "terms_set".to_string(),
            field: "minimum_should_match".to_string(),
            reason: "must fit in usize".to_string(),
        })?;

    for option in field_object.keys() {
        if option != "terms"
            && option != "minimum_should_match"
            && option != "minimum_should_match_script"
        {
            return Err(QueryDslError::UnsupportedOption {
                clause: "terms_set".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::TermsSet {
        field: field.clone(),
        values,
        minimum_should_match,
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
        if let Some(query) = object.get("query") {
            query.clone()
        } else if object.keys().any(|key| {
            matches!(
                key.as_str(),
                "analyzer"
                    | "auto_generate_synonyms_phrase_query"
                    | "boost"
                    | "cutoff_frequency"
                    | "fuzziness"
                    | "fuzzy_rewrite"
                    | "fuzzy_transpositions"
                    | "lenient"
                    | "max_expansions"
                    | "minimum_should_match"
                    | "operator"
                    | "prefix_length"
                    | "zero_terms_query"
            )
        }) {
            return Err(QueryDslError::MissingField {
                clause: "match".to_string(),
                field: "query".to_string(),
            });
        } else {
            match_body.clone()
        }
    } else {
        match_body.clone()
    };

    Ok(Query::Match {
        field: field.clone(),
        query,
    })
}

fn parse_match_phrase(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if object.len() != 1 {
        return Err(QueryDslError::ExpectedSingleField {
            clause: "match_phrase".to_string(),
        });
    }

    let (field, match_body) = object.iter().next().expect("checked len");
    let query = if let Some(object) = match_body.as_object() {
        object
            .get("query")
            .cloned()
            .ok_or_else(|| QueryDslError::MissingField {
                clause: "match_phrase".to_string(),
                field: "query".to_string(),
            })?
    } else {
        match_body.clone()
    };

    Ok(Query::MatchPhrase {
        field: field.clone(),
        query,
    })
}

fn parse_match_phrase_prefix(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if object.len() != 1 {
        return Err(QueryDslError::ExpectedSingleField {
            clause: "match_phrase_prefix".to_string(),
        });
    }

    let (field, match_body) = object.iter().next().expect("checked len");
    let query = if let Some(object) = match_body.as_object() {
        object
            .get("query")
            .cloned()
            .ok_or_else(|| QueryDslError::MissingField {
                clause: "match_phrase_prefix".to_string(),
                field: "query".to_string(),
            })?
    } else {
        match_body.clone()
    };

    Ok(Query::MatchPhrasePrefix {
        field: field.clone(),
        query,
    })
}

fn parse_match_bool_prefix(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if object.len() != 1 {
        return Err(QueryDslError::ExpectedSingleField {
            clause: "match_bool_prefix".to_string(),
        });
    }

    let (field, match_body) = object.iter().next().expect("checked len");
    let query = if let Some(object) = match_body.as_object() {
        object
            .get("query")
            .cloned()
            .ok_or_else(|| QueryDslError::MissingField {
                clause: "match_bool_prefix".to_string(),
                field: "query".to_string(),
            })?
    } else {
        match_body.clone()
    };

    Ok(Query::MatchBoolPrefix {
        field: field.clone(),
        query,
    })
}

fn parse_multi_match(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let query = object
        .get("query")
        .cloned()
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "multi_match".to_string(),
            field: "query".to_string(),
        })?;
    let fields = object
        .get("fields")
        .and_then(Value::as_array)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "multi_match".to_string(),
            field: "fields".to_string(),
        })?
        .iter()
        .map(|value| {
            value
                .as_str()
                .map(ToString::to_string)
                .ok_or(QueryDslError::ExpectedObject)
        })
        .collect::<QueryDslResult<Vec<_>>>()?;

    if let Some(query_type) = object.get("type").and_then(Value::as_str) {
        if query_type != "best_fields" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "multi_match".to_string(),
                option: "type".to_string(),
            });
        }
    }
    for option in object.keys() {
        if option != "query" && option != "fields" && option != "type" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "multi_match".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::MultiMatch { fields, query })
}

fn parse_combined_fields(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let query = object
        .get("query")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "combined_fields".to_string(),
            field: "query".to_string(),
        })?
        .to_string();
    let fields = object
        .get("fields")
        .and_then(Value::as_array)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "combined_fields".to_string(),
            field: "fields".to_string(),
        })?
        .iter()
        .map(|value| {
            value
                .as_str()
                .map(ToString::to_string)
                .ok_or(QueryDslError::ExpectedObject)
        })
        .collect::<QueryDslResult<Vec<_>>>()?;

    for option in object.keys() {
        if option != "query" && option != "fields" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "combined_fields".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::CombinedFields { query, fields })
}

fn parse_simple_query_string(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let query = object
        .get("query")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "simple_query_string".to_string(),
            field: "query".to_string(),
        })?
        .to_string();
    let fields = object
        .get("fields")
        .map(|value| {
            value
                .as_array()
                .ok_or(QueryDslError::ExpectedObject)?
                .iter()
                .map(|value| {
                    value
                        .as_str()
                        .map(ToString::to_string)
                        .ok_or(QueryDslError::ExpectedObject)
                })
                .collect::<QueryDslResult<Vec<_>>>()
        })
        .transpose()?;

    for option in object.keys() {
        if option != "query" && option != "fields" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "simple_query_string".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::SimpleQueryString { query, fields })
}

fn parse_query_string(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let query = object
        .get("query")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "query_string".to_string(),
            field: "query".to_string(),
        })?
        .to_string();
    let fields = object
        .get("fields")
        .map(|value| {
            value
                .as_array()
                .ok_or(QueryDslError::ExpectedObject)?
                .iter()
                .map(|value| {
                    value
                        .as_str()
                        .map(ToString::to_string)
                        .ok_or(QueryDslError::ExpectedObject)
                })
                .collect::<QueryDslResult<Vec<_>>>()
        })
        .transpose()?;

    for option in object.keys() {
        if option != "query" && option != "fields" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "query_string".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::QueryString { query, fields })
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

fn parse_rank_feature(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let field = object
        .get("field")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "rank_feature".to_string(),
            field: "field".to_string(),
        })?
        .to_string();

    for (option, _) in object {
        if option != "field" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "rank_feature".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::RankFeature { field })
}

fn parse_distance_feature(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let field = object
        .get("field")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "distance_feature".to_string(),
            field: "field".to_string(),
        })?
        .to_string();
    let origin = object
        .get("origin")
        .cloned()
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "distance_feature".to_string(),
            field: "origin".to_string(),
        })?;
    let pivot = object
        .get("pivot")
        .cloned()
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "distance_feature".to_string(),
            field: "pivot".to_string(),
        })?;

    for (option, _) in object {
        if option != "field" && option != "origin" && option != "pivot" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "distance_feature".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::DistanceFeature {
        field,
        origin,
        pivot,
    })
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

fn parse_regexp(body: &Value) -> QueryDslResult<Query> {
    let (field, value, case_insensitive) =
        parse_string_multiterm("regexp", body, &["value", "regexp"])?;
    Ok(Query::Regexp {
        field,
        value,
        case_insensitive,
    })
}

fn parse_fuzzy(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if object.len() != 1 {
        return Err(QueryDslError::ExpectedSingleField {
            clause: "fuzzy".to_string(),
        });
    }

    let (field, body) = object.iter().next().expect("single fuzzy field");
    match body {
        Value::String(value) => Ok(Query::Fuzzy {
            field: field.clone(),
            value: value.clone(),
            fuzziness: 2,
            prefix_length: 0,
            transpositions: true,
        }),
        Value::Object(options) => {
            let value = options
                .get("value")
                .or_else(|| options.get("fuzzy"))
                .and_then(Value::as_str)
                .ok_or_else(|| QueryDslError::MissingField {
                    clause: "fuzzy".to_string(),
                    field: "value".to_string(),
                })?
                .to_string();
            let fuzziness = match options.get("fuzziness") {
                None => 2,
                Some(Value::Number(number)) => number
                    .as_u64()
                    .and_then(|value| u8::try_from(value).ok())
                    .ok_or_else(|| QueryDslError::UnsupportedOption {
                        clause: "fuzzy".to_string(),
                        option: "fuzziness".to_string(),
                    })?,
                Some(Value::String(text)) => {
                    text.parse::<u8>()
                        .map_err(|_| QueryDslError::UnsupportedOption {
                            clause: "fuzzy".to_string(),
                            option: "fuzziness".to_string(),
                        })?
                }
                Some(_) => {
                    return Err(QueryDslError::UnsupportedOption {
                        clause: "fuzzy".to_string(),
                        option: "fuzziness".to_string(),
                    })
                }
            };
            let prefix_length = match options.get("prefix_length") {
                None => 0,
                Some(value) => parse_usize_option("fuzzy", "prefix_length", value)?,
            };
            let transpositions = options
                .get("transpositions")
                .map(Value::as_bool)
                .unwrap_or(Some(true))
                .ok_or_else(|| QueryDslError::UnsupportedOption {
                    clause: "fuzzy".to_string(),
                    option: "transpositions".to_string(),
                })?;

            for option in options.keys() {
                if option != "value"
                    && option != "fuzzy"
                    && option != "fuzziness"
                    && option != "prefix_length"
                    && option != "transpositions"
                {
                    return Err(QueryDslError::UnsupportedOption {
                        clause: "fuzzy".to_string(),
                        option: option.clone(),
                    });
                }
            }

            Ok(Query::Fuzzy {
                field: field.clone(),
                value,
                fuzziness,
                prefix_length,
                transpositions,
            })
        }
        _ => Err(QueryDslError::ExpectedObject),
    }
}

fn parse_wrapper(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let encoded_query =
        object
            .get("query")
            .and_then(Value::as_str)
            .ok_or_else(|| QueryDslError::MissingField {
                clause: "wrapper".to_string(),
                field: "query".to_string(),
            })?;

    for option in object.keys() {
        if option != "query" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "wrapper".to_string(),
                option: option.clone(),
            });
        }
    }

    let decoded = STANDARD
        .decode(encoded_query)
        .map_err(|error| QueryDslError::InvalidValue {
            clause: "wrapper".to_string(),
            field: "query".to_string(),
            reason: format!("invalid base64 payload: {error}"),
        })?;
    let decoded = String::from_utf8(decoded).map_err(|error| QueryDslError::InvalidValue {
        clause: "wrapper".to_string(),
        field: "query".to_string(),
        reason: format!("decoded wrapper payload is not utf-8: {error}"),
    })?;
    let decoded_value =
        serde_json::from_str::<Value>(&decoded).map_err(|error| QueryDslError::InvalidValue {
            clause: "wrapper".to_string(),
            field: "query".to_string(),
            reason: format!("decoded wrapper payload is not valid json: {error}"),
        })?;

    Ok(Query::Wrapper {
        query: Box::new(parse_query(&decoded_value)?),
    })
}

fn parse_nested(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let path = object
        .get("path")
        .and_then(Value::as_str)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "nested".to_string(),
            field: "path".to_string(),
        })?
        .to_string();
    let query = object
        .get("query")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "nested".to_string(),
            field: "query".to_string(),
        })
        .and_then(parse_query)?;

    for option in object.keys() {
        if option != "path" && option != "query" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "nested".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::Nested {
        path,
        query: Box::new(query),
    })
}

fn parse_pinned(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let ids = object
        .get("ids")
        .and_then(Value::as_array)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "pinned".to_string(),
            field: "ids".to_string(),
        })?
        .iter()
        .map(|value| {
            value
                .as_str()
                .map(ToOwned::to_owned)
                .ok_or_else(|| QueryDslError::InvalidValue {
                    clause: "pinned".to_string(),
                    field: "ids".to_string(),
                    reason: "must contain only strings".to_string(),
                })
        })
        .collect::<QueryDslResult<Vec<_>>>()?;
    let organic = object
        .get("organic")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "pinned".to_string(),
            field: "organic".to_string(),
        })
        .and_then(parse_query)?;

    for option in object.keys() {
        if option != "ids" && option != "organic" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "pinned".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::Pinned {
        ids,
        organic: Box::new(organic),
    })
}

fn parse_more_like_this(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let fields = object
        .get("fields")
        .map(|value| {
            value
                .as_array()
                .ok_or_else(|| QueryDslError::InvalidValue {
                    clause: "more_like_this".to_string(),
                    field: "fields".to_string(),
                    reason: "must be an array of strings".to_string(),
                })?
                .iter()
                .map(|value| {
                    value.as_str().map(ToOwned::to_owned).ok_or_else(|| {
                        QueryDslError::InvalidValue {
                            clause: "more_like_this".to_string(),
                            field: "fields".to_string(),
                            reason: "must contain only strings".to_string(),
                        }
                    })
                })
                .collect::<QueryDslResult<Vec<_>>>()
        })
        .transpose()?;
    let like = match object.get("like") {
        Some(Value::String(text)) => vec![text.clone()],
        Some(Value::Array(values)) => values
            .iter()
            .map(|value| {
                value
                    .as_str()
                    .map(ToOwned::to_owned)
                    .ok_or_else(|| QueryDslError::InvalidValue {
                        clause: "more_like_this".to_string(),
                        field: "like".to_string(),
                        reason: "must contain only strings".to_string(),
                    })
            })
            .collect::<QueryDslResult<Vec<_>>>()?,
        Some(_) => {
            return Err(QueryDslError::InvalidValue {
                clause: "more_like_this".to_string(),
                field: "like".to_string(),
                reason: "must be a string or array of strings".to_string(),
            })
        }
        None => {
            return Err(QueryDslError::MissingField {
                clause: "more_like_this".to_string(),
                field: "like".to_string(),
            })
        }
    };

    for option in object.keys() {
        if !matches!(
            option.as_str(),
            "fields" | "like" | "min_term_freq" | "min_doc_freq" | "max_query_terms"
        ) {
            return Err(QueryDslError::UnsupportedOption {
                clause: "more_like_this".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::MoreLikeThis { fields, like })
}

fn parse_constant_score(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let filter = object
        .get("filter")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "constant_score".to_string(),
            field: "filter".to_string(),
        })
        .and_then(parse_query)?;

    for option in object.keys() {
        if option != "filter" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "constant_score".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::ConstantScore {
        filter: Box::new(filter),
    })
}

fn parse_dis_max(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let queries = object
        .get("queries")
        .and_then(Value::as_array)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "dis_max".to_string(),
            field: "queries".to_string(),
        })?
        .iter()
        .map(parse_query)
        .collect::<QueryDslResult<Vec<_>>>()?;
    let tie_breaker = object.get("tie_breaker").and_then(Value::as_f64);

    for option in object.keys() {
        if option != "queries" && option != "tie_breaker" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "dis_max".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::DisMax {
        queries,
        tie_breaker,
    })
}

fn parse_boosting(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let positive = object
        .get("positive")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "boosting".to_string(),
            field: "positive".to_string(),
        })
        .and_then(parse_query)?;
    let negative = object
        .get("negative")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "boosting".to_string(),
            field: "negative".to_string(),
        })
        .and_then(parse_query)?;
    let negative_boost = object
        .get("negative_boost")
        .and_then(Value::as_f64)
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "boosting".to_string(),
            field: "negative_boost".to_string(),
        })?;

    for option in object.keys() {
        if option != "positive" && option != "negative" && option != "negative_boost" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "boosting".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::Boosting {
        positive: Box::new(positive),
        negative: Box::new(negative),
        negative_boost,
    })
}

fn parse_function_score(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let query = object
        .get("query")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "function_score".to_string(),
            field: "query".to_string(),
        })
        .and_then(parse_query)?;

    for option in object.keys() {
        if option != "query" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "function_score".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::FunctionScore {
        query: Box::new(query),
    })
}

fn parse_script_score(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let query = object
        .get("query")
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "script_score".to_string(),
            field: "query".to_string(),
        })
        .and_then(parse_query)?;
    let script = object
        .get("script")
        .cloned()
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "script_score".to_string(),
            field: "script".to_string(),
        })?;

    for option in object.keys() {
        if option != "query" && option != "script" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "script_score".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::ScriptScore {
        query: Box::new(query),
        script,
    })
}

fn parse_script(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let script = object
        .get("script")
        .cloned()
        .ok_or_else(|| QueryDslError::MissingField {
            clause: "script".to_string(),
            field: "script".to_string(),
        })?;

    if !(script.is_string()
        || script
            .as_object()
            .and_then(|script_object| script_object.get("source"))
            .and_then(Value::as_str)
            .is_some())
    {
        return Err(QueryDslError::UnsupportedOption {
            clause: "script".to_string(),
            option: "script".to_string(),
        });
    }

    for option in object.keys() {
        if option != "script" && option != "_name" && option != "boost" {
            return Err(QueryDslError::UnsupportedOption {
                clause: "script".to_string(),
                option: option.clone(),
            });
        }
    }

    Ok(Query::Script { script })
}

fn parse_intervals(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if object.len() != 1 {
        return Err(QueryDslError::ExpectedSingleField {
            clause: "intervals".to_string(),
        });
    }
    let (field, spec) = object.iter().next().expect("checked len");
    let spec_object = spec.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let interval_rule_count = spec_object
        .keys()
        .filter(|key| key.as_str() != "_name" && key.as_str() != "boost")
        .count();
    if interval_rule_count != 1 {
        return Err(QueryDslError::ExpectedSingleField {
            clause: "intervals".to_string(),
        });
    }
    if !intervals_spec_is_supported(spec) {
        return Err(QueryDslError::UnsupportedOption {
            clause: "intervals".to_string(),
            option: "rule".to_string(),
        });
    }
    Ok(Query::Intervals {
        field: field.clone(),
        spec: spec.clone(),
    })
}

fn parse_template(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    if object.is_empty() {
        return Err(QueryDslError::ExpectedSingleClause);
    }
    parse_query(&Value::Object(object.clone()))
}

fn intervals_spec_is_supported(spec: &Value) -> bool {
    let Some(object) = spec.as_object() else {
        return false;
    };
    if let Some(match_spec) = object.get("match").and_then(Value::as_object) {
        return match_spec
            .get("query")
            .and_then(Value::as_str)
            .is_some_and(|query| !query.is_empty())
            && match_spec
                .keys()
                .all(|key| key == "query" || key == "ordered" || key == "max_gaps");
    }
    if let Some(all_of) = object.get("all_of").and_then(Value::as_object) {
        let Some(intervals) = all_of.get("intervals").and_then(Value::as_array) else {
            return false;
        };
        return !intervals.is_empty()
            && all_of
                .keys()
                .all(|key| key == "intervals" || key == "ordered" || key == "max_gaps")
            && intervals.iter().all(|interval| {
                interval
                    .get("match")
                    .and_then(Value::as_object)
                    .and_then(|match_spec| match_spec.get("query"))
                    .and_then(Value::as_str)
                    .is_some_and(|query| !query.is_empty())
            });
    }
    false
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

fn parse_geo_distance(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let distance_meters =
        parse_geo_distance_distance(object.get("distance").ok_or_else(|| {
            QueryDslError::MissingField {
                clause: "geo_distance".to_string(),
                field: "distance".to_string(),
            }
        })?)?;
    let ignore_unmapped = object
        .get("ignore_unmapped")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    let mut field_name = None;
    let mut lat = None;
    let mut lon = None;
    for (option, value) in object {
        match option.as_str() {
            "distance" | "ignore_unmapped" => {}
            field => {
                let point = value.as_object().ok_or(QueryDslError::ExpectedObject)?;
                lat = point.get("lat").and_then(Value::as_f64);
                lon = point.get("lon").and_then(Value::as_f64);
                field_name = Some(field.to_string());
            }
        }
    }
    let field = field_name.ok_or_else(|| QueryDslError::ExpectedSingleField {
        clause: "geo_distance".to_string(),
    })?;
    let lat = lat.ok_or_else(|| QueryDslError::MissingField {
        clause: "geo_distance".to_string(),
        field: "lat".to_string(),
    })?;
    let lon = lon.ok_or_else(|| QueryDslError::MissingField {
        clause: "geo_distance".to_string(),
        field: "lon".to_string(),
    })?;
    Ok(Query::GeoDistance(GeoDistanceQuery {
        field,
        distance_meters,
        lat,
        lon,
        ignore_unmapped,
    }))
}

fn parse_geo_bounding_box(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let ignore_unmapped = object
        .get("ignore_unmapped")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    let mut field_name = None;
    let mut top_left = None;
    let mut bottom_right = None;
    for (option, value) in object {
        match option.as_str() {
            "ignore_unmapped" | "validation_method" | "type" | "_name" | "boost" => {}
            field => {
                let box_object = value.as_object().ok_or(QueryDslError::ExpectedObject)?;
                top_left = box_object.get("top_left").and_then(parse_geo_point_object);
                bottom_right = box_object
                    .get("bottom_right")
                    .and_then(parse_geo_point_object);
                field_name = Some(field.to_string());
            }
        }
    }
    let field = field_name.ok_or_else(|| QueryDslError::ExpectedSingleField {
        clause: "geo_bounding_box".to_string(),
    })?;
    let (top, left) = top_left.ok_or_else(|| QueryDslError::MissingField {
        clause: "geo_bounding_box".to_string(),
        field: "top_left".to_string(),
    })?;
    let (bottom, right) = bottom_right.ok_or_else(|| QueryDslError::MissingField {
        clause: "geo_bounding_box".to_string(),
        field: "bottom_right".to_string(),
    })?;
    Ok(Query::GeoBoundingBox(GeoBoundingBoxQuery {
        field,
        top,
        left,
        bottom,
        right,
        ignore_unmapped,
    }))
}

fn parse_geo_polygon(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let ignore_unmapped = object
        .get("ignore_unmapped")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    let mut field_name = None;
    let mut points = None;
    for (option, value) in object {
        match option.as_str() {
            "ignore_unmapped" | "validation_method" | "_name" | "boost" => {}
            field => {
                let polygon_object = value.as_object().ok_or(QueryDslError::ExpectedObject)?;
                let parsed_points = polygon_object
                    .get("points")
                    .and_then(Value::as_array)
                    .ok_or_else(|| QueryDslError::MissingField {
                        clause: "geo_polygon".to_string(),
                        field: "points".to_string(),
                    })?
                    .iter()
                    .map(parse_geo_point)
                    .collect::<Option<Vec<_>>>()
                    .ok_or_else(|| QueryDslError::InvalidValue {
                        clause: "geo_polygon".to_string(),
                        field: "points".to_string(),
                        reason: "invalid geo point".to_string(),
                    })?;
                field_name = Some(field.to_string());
                points = Some(parsed_points);
            }
        }
    }
    let field = field_name.ok_or_else(|| QueryDslError::ExpectedSingleField {
        clause: "geo_polygon".to_string(),
    })?;
    let mut points = points.ok_or_else(|| QueryDslError::MissingField {
        clause: "geo_polygon".to_string(),
        field: "points".to_string(),
    })?;
    let already_closed = points.first() == points.last();
    if points.len() < 3 || (already_closed && points.len() < 4) {
        return Err(QueryDslError::InvalidValue {
            clause: "geo_polygon".to_string(),
            field: "points".to_string(),
            reason: "too few points defined for geo_polygon query".to_string(),
        });
    }
    if !already_closed {
        if let Some(first) = points.first().cloned() {
            points.push(first);
        }
    }
    Ok(Query::GeoPolygon(GeoPolygonQuery {
        field,
        points,
        ignore_unmapped,
    }))
}

fn parse_geo_shape(body: &Value) -> QueryDslResult<Query> {
    let object = body.as_object().ok_or(QueryDslError::ExpectedObject)?;
    let ignore_unmapped = object
        .get("ignore_unmapped")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    let mut field_name = None;
    let mut shape = None;
    let mut relation = "intersects".to_string();
    for (option, value) in object {
        match option.as_str() {
            "ignore_unmapped" | "_name" | "boost" => {}
            field => {
                let shape_object = value.as_object().ok_or(QueryDslError::ExpectedObject)?;
                for key in shape_object.keys() {
                    if !matches!(key.as_str(), "shape" | "relation" | "strategy") {
                        return Err(QueryDslError::UnsupportedOption {
                            clause: "geo_shape".to_string(),
                            option: key.clone(),
                        });
                    }
                }
                let parsed_shape =
                    shape_object
                        .get("shape")
                        .ok_or_else(|| QueryDslError::MissingField {
                            clause: "geo_shape".to_string(),
                            field: "shape".to_string(),
                        })?;
                validate_geo_shape(parsed_shape)?;
                if let Some(parsed_relation) = shape_object.get("relation").and_then(Value::as_str)
                {
                    let normalized = parsed_relation.to_ascii_lowercase();
                    if !matches!(normalized.as_str(), "intersects" | "within" | "contains") {
                        return Err(QueryDslError::UnsupportedOption {
                            clause: "geo_shape".to_string(),
                            option: "relation".to_string(),
                        });
                    }
                    relation = normalized;
                }
                field_name = Some(field.to_string());
                shape = Some(parsed_shape.clone());
            }
        }
    }
    let field = field_name.ok_or_else(|| QueryDslError::ExpectedSingleField {
        clause: "geo_shape".to_string(),
    })?;
    let shape = shape.ok_or_else(|| QueryDslError::MissingField {
        clause: "geo_shape".to_string(),
        field: "shape".to_string(),
    })?;
    Ok(Query::GeoShape(GeoShapeQuery {
        field,
        shape,
        relation,
        ignore_unmapped,
    }))
}

fn validate_geo_shape(shape: &Value) -> QueryDslResult<()> {
    if geo_shape_point(shape).is_some()
        || geo_shape_envelope(shape).is_some()
        || geo_shape_polygon(shape).is_some()
    {
        Ok(())
    } else {
        Err(QueryDslError::InvalidValue {
            clause: "geo_shape".to_string(),
            field: "shape".to_string(),
            reason: "unsupported geo shape".to_string(),
        })
    }
}

fn geo_shape_type(shape: &Value) -> Option<String> {
    shape
        .as_object()?
        .get("type")?
        .as_str()
        .map(|value| value.to_ascii_lowercase())
}

fn geo_shape_point(shape: &Value) -> Option<GeoPoint> {
    if geo_shape_type(shape)?.as_str() != "point" {
        return None;
    }
    let coordinates = shape.as_object()?.get("coordinates")?.as_array()?;
    if coordinates.len() != 2 {
        return None;
    }
    Some(GeoPoint {
        lon: coordinates[0].as_f64()?,
        lat: coordinates[1].as_f64()?,
    })
}

fn geo_shape_envelope(shape: &Value) -> Option<(GeoPoint, GeoPoint)> {
    if geo_shape_type(shape)?.as_str() != "envelope" {
        return None;
    }
    let coordinates = shape.as_object()?.get("coordinates")?.as_array()?;
    if coordinates.len() != 2 {
        return None;
    }
    let top_left = parse_geo_point(&coordinates[0])?;
    let bottom_right = parse_geo_point(&coordinates[1])?;
    Some((top_left, bottom_right))
}

fn geo_shape_polygon(shape: &Value) -> Option<Vec<GeoPoint>> {
    if geo_shape_type(shape)?.as_str() != "polygon" {
        return None;
    }
    let rings = shape.as_object()?.get("coordinates")?.as_array()?;
    let first_ring = rings.first()?.as_array()?;
    let mut points = first_ring
        .iter()
        .map(parse_geo_point)
        .collect::<Option<Vec<_>>>()?;
    let already_closed = points.first() == points.last();
    if points.len() < 3 || (already_closed && points.len() < 4) {
        return None;
    }
    if !already_closed {
        if let Some(first) = points.first().cloned() {
            points.push(first);
        }
    }
    Some(points)
}

fn parse_geo_point(value: &Value) -> Option<GeoPoint> {
    if let Some(object) = value.as_object() {
        return Some(GeoPoint {
            lat: object.get("lat")?.as_f64()?,
            lon: object.get("lon")?.as_f64()?,
        });
    }
    let array = value.as_array()?;
    if array.len() != 2 {
        return None;
    }
    Some(GeoPoint {
        lon: array[0].as_f64()?,
        lat: array[1].as_f64()?,
    })
}

fn parse_geo_point_object(value: &Value) -> Option<(f64, f64)> {
    let point = value.as_object()?;
    Some((point.get("lat")?.as_f64()?, point.get("lon")?.as_f64()?))
}

fn parse_geo_distance_distance(value: &Value) -> QueryDslResult<f64> {
    match value {
        Value::Number(number) => number.as_f64().ok_or_else(|| QueryDslError::InvalidValue {
            clause: "geo_distance".to_string(),
            field: "distance".to_string(),
            reason: "must be a finite number".to_string(),
        }),
        Value::String(text) => {
            let lower = text.trim().to_ascii_lowercase();
            let parse_prefixed = |suffix: &str, multiplier: f64| -> Option<QueryDslResult<f64>> {
                lower.strip_suffix(suffix).map(|prefix| {
                    prefix
                        .trim()
                        .parse::<f64>()
                        .map(|value| value * multiplier)
                        .map_err(|_| QueryDslError::InvalidValue {
                            clause: "geo_distance".to_string(),
                            field: "distance".to_string(),
                            reason: format!("unsupported distance literal [{text}]"),
                        })
                })
            };
            if let Some(result) = parse_prefixed("km", 1000.0) {
                return result;
            }
            if let Some(result) = parse_prefixed("m", 1.0) {
                return result;
            }
            lower
                .parse::<f64>()
                .map_err(|_| QueryDslError::InvalidValue {
                    clause: "geo_distance".to_string(),
                    field: "distance".to_string(),
                    reason: format!("unsupported distance literal [{text}]"),
                })
        }
        _ => Err(QueryDslError::InvalidValue {
            clause: "geo_distance".to_string(),
            field: "distance".to_string(),
            reason: "must be a number or distance string".to_string(),
        }),
    }
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
    fn parses_prefix_wildcard_and_regexp_queries() {
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
        let regexp = parse_query(&serde_json::json!({
            "regexp": {
                "message": {
                    "value": "err.*",
                    "case_insensitive": true
                }
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
        assert_eq!(
            regexp,
            Query::Regexp {
                field: "message".to_string(),
                value: "err.*".to_string(),
                case_insensitive: true
            }
        );
    }

    #[test]
    fn parses_fuzzy_queries() {
        let shorthand = parse_query(&serde_json::json!({
            "fuzzy": {
                "message": "alpah"
            }
        }))
        .unwrap();
        let explicit = parse_query(&serde_json::json!({
            "fuzzy": {
                "message": {
                    "value": "alpah",
                    "fuzziness": 1,
                    "prefix_length": 1,
                    "transpositions": false
                }
            }
        }))
        .unwrap();

        assert_eq!(
            shorthand,
            Query::Fuzzy {
                field: "message".to_string(),
                value: "alpah".to_string(),
                fuzziness: 2,
                prefix_length: 0,
                transpositions: true,
            }
        );
        assert_eq!(
            explicit,
            Query::Fuzzy {
                field: "message".to_string(),
                value: "alpah".to_string(),
                fuzziness: 1,
                prefix_length: 1,
                transpositions: false,
            }
        );
    }

    #[test]
    fn parses_match_phrase_queries() {
        let shorthand = parse_query(&serde_json::json!({
            "match_phrase": {
                "message": "alpha checkout"
            }
        }))
        .unwrap();
        let explicit = parse_query(&serde_json::json!({
            "match_phrase": {
                "message": {
                    "query": "alpha checkout"
                }
            }
        }))
        .unwrap();

        assert_eq!(
            shorthand,
            Query::MatchPhrase {
                field: "message".to_string(),
                query: serde_json::json!("alpha checkout"),
            }
        );
        assert_eq!(
            explicit,
            Query::MatchPhrase {
                field: "message".to_string(),
                query: serde_json::json!("alpha checkout"),
            }
        );
    }

    #[test]
    fn parses_match_phrase_prefix_queries() {
        let shorthand = parse_query(&serde_json::json!({
            "match_phrase_prefix": {
                "message": "alpha check"
            }
        }))
        .unwrap();
        let explicit = parse_query(&serde_json::json!({
            "match_phrase_prefix": {
                "message": {
                    "query": "alpha check"
                }
            }
        }))
        .unwrap();

        assert_eq!(
            shorthand,
            Query::MatchPhrasePrefix {
                field: "message".to_string(),
                query: serde_json::json!("alpha check"),
            }
        );
        assert_eq!(
            explicit,
            Query::MatchPhrasePrefix {
                field: "message".to_string(),
                query: serde_json::json!("alpha check"),
            }
        );
    }

    #[test]
    fn parses_match_bool_prefix_queries() {
        let shorthand = parse_query(&serde_json::json!({
            "match_bool_prefix": {
                "message": "alpha check"
            }
        }))
        .unwrap();
        let explicit = parse_query(&serde_json::json!({
            "match_bool_prefix": {
                "message": {
                    "query": "alpha check"
                }
            }
        }))
        .unwrap();

        assert_eq!(
            shorthand,
            Query::MatchBoolPrefix {
                field: "message".to_string(),
                query: serde_json::json!("alpha check"),
            }
        );
        assert_eq!(
            explicit,
            Query::MatchBoolPrefix {
                field: "message".to_string(),
                query: serde_json::json!("alpha check"),
            }
        );
    }

    #[test]
    fn parses_combined_fields_queries() {
        let query = parse_query(&serde_json::json!({
            "combined_fields": {
                "query": "alpha beta",
                "fields": ["title", "body"]
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::CombinedFields {
                query: "alpha beta".to_string(),
                fields: vec!["title".to_string(), "body".to_string()],
            }
        );
    }

    #[test]
    fn parses_multi_match_queries() {
        let query = parse_query(&serde_json::json!({
            "multi_match": {
                "query": "alpha",
                "fields": ["title", "body"]
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::MultiMatch {
                fields: vec!["title".to_string(), "body".to_string()],
                query: serde_json::json!("alpha"),
            }
        );
    }

    #[test]
    fn parses_simple_query_string_queries() {
        let query = parse_query(&serde_json::json!({
            "simple_query_string": {
                "query": "alpha beta",
                "fields": ["title", "body"]
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::SimpleQueryString {
                query: "alpha beta".to_string(),
                fields: Some(vec!["title".to_string(), "body".to_string()]),
            }
        );
    }

    #[test]
    fn parses_query_string_queries() {
        let query = parse_query(&serde_json::json!({
            "query_string": {
                "query": "alpha beta",
                "fields": ["title", "body"]
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::QueryString {
                query: "alpha beta".to_string(),
                fields: Some(vec!["title".to_string(), "body".to_string()]),
            }
        );
    }

    #[test]
    fn parses_terms_set_queries() {
        let query = parse_query(&serde_json::json!({
            "terms_set": {
                "tags": {
                    "terms": ["alpha", "beta"],
                    "minimum_should_match": 2
                }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::TermsSet {
                field: "tags".to_string(),
                values: vec![serde_json::json!("alpha"), serde_json::json!("beta")],
                minimum_should_match: 2,
            }
        );
    }

    #[test]
    fn parses_span_term_queries() {
        let query = parse_query(&serde_json::json!({
            "span_term": {
                "service": "api"
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::SpanTerm {
                field: "service".to_string(),
                value: serde_json::json!("api"),
            }
        );
    }

    #[test]
    fn parses_span_or_queries() {
        let query = parse_query(&serde_json::json!({
            "span_or": {
                "clauses": [
                    { "span_term": { "service": "api" } },
                    { "span_term": { "service": "worker" } }
                ]
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::SpanOr {
                clauses: vec![
                    Query::SpanTerm {
                        field: "service".to_string(),
                        value: serde_json::json!("api"),
                    },
                    Query::SpanTerm {
                        field: "service".to_string(),
                        value: serde_json::json!("worker"),
                    },
                ],
            }
        );
    }

    #[test]
    fn parses_span_first_queries() {
        let query = parse_query(&serde_json::json!({
            "span_first": {
                "match": {
                    "span_term": { "message": "alpha" }
                },
                "end": 1
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::SpanFirst {
                match_query: Box::new(Query::SpanTerm {
                    field: "message".to_string(),
                    value: serde_json::json!("alpha"),
                }),
                end: 1,
            }
        );
    }

    #[test]
    fn parses_span_near_queries() {
        let query = parse_query(&serde_json::json!({
            "span_near": {
                "clauses": [
                    { "span_term": { "message": "alpha" } },
                    { "span_term": { "message": "beta" } }
                ],
                "slop": 1,
                "in_order": true
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::SpanNear {
                clauses: vec![
                    Query::SpanTerm {
                        field: "message".to_string(),
                        value: serde_json::json!("alpha"),
                    },
                    Query::SpanTerm {
                        field: "message".to_string(),
                        value: serde_json::json!("beta"),
                    },
                ],
                slop: 1,
                in_order: true,
            }
        );
    }

    #[test]
    fn parses_span_gap_clause_queries() {
        let query = parse_query(&serde_json::json!({
            "span_near": {
                "clauses": [
                    { "span_term": { "message": "alpha" } },
                    { "span_gap": { "message": 2 } },
                    { "span_term": { "message": "delta" } }
                ],
                "slop": 0,
                "in_order": true
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::SpanNear {
                clauses: vec![
                    Query::SpanTerm {
                        field: "message".to_string(),
                        value: serde_json::json!("alpha"),
                    },
                    Query::SpanGap {
                        field: "message".to_string(),
                        width: 2,
                    },
                    Query::SpanTerm {
                        field: "message".to_string(),
                        value: serde_json::json!("delta"),
                    },
                ],
                slop: 0,
                in_order: true,
            }
        );
    }

    #[test]
    fn parses_span_not_queries() {
        let query = parse_query(&serde_json::json!({
            "span_not": {
                "include": {
                    "span_term": { "message": "alpha" }
                },
                "exclude": {
                    "span_term": { "message": "beta" }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::SpanNot {
                include: Box::new(Query::SpanTerm {
                    field: "message".to_string(),
                    value: serde_json::json!("alpha"),
                }),
                exclude: Box::new(Query::SpanTerm {
                    field: "message".to_string(),
                    value: serde_json::json!("beta"),
                }),
            }
        );
    }

    #[test]
    fn parses_span_containing_queries() {
        let query = parse_query(&serde_json::json!({
            "span_containing": {
                "big": {
                    "span_near": {
                        "clauses": [
                            { "span_term": { "message": "alpha" } },
                            { "span_term": { "message": "beta" } }
                        ],
                        "slop": 1,
                        "in_order": true
                    }
                },
                "little": {
                    "span_term": { "message": "beta" }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::SpanContaining {
                big: Box::new(Query::SpanNear {
                    clauses: vec![
                        Query::SpanTerm {
                            field: "message".to_string(),
                            value: serde_json::json!("alpha"),
                        },
                        Query::SpanTerm {
                            field: "message".to_string(),
                            value: serde_json::json!("beta"),
                        },
                    ],
                    slop: 1,
                    in_order: true,
                }),
                little: Box::new(Query::SpanTerm {
                    field: "message".to_string(),
                    value: serde_json::json!("beta"),
                }),
            }
        );
    }

    #[test]
    fn parses_span_within_queries() {
        let query = parse_query(&serde_json::json!({
            "span_within": {
                "big": {
                    "span_near": {
                        "clauses": [
                            { "span_term": { "message": "alpha" } },
                            { "span_term": { "message": "beta" } }
                        ],
                        "slop": 1,
                        "in_order": true
                    }
                },
                "little": {
                    "span_term": { "message": "alpha" }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::SpanWithin {
                big: Box::new(Query::SpanNear {
                    clauses: vec![
                        Query::SpanTerm {
                            field: "message".to_string(),
                            value: serde_json::json!("alpha"),
                        },
                        Query::SpanTerm {
                            field: "message".to_string(),
                            value: serde_json::json!("beta"),
                        },
                    ],
                    slop: 1,
                    in_order: true,
                }),
                little: Box::new(Query::SpanTerm {
                    field: "message".to_string(),
                    value: serde_json::json!("alpha"),
                }),
            }
        );
    }

    #[test]
    fn parses_span_multi_queries() {
        let query = parse_query(&serde_json::json!({
            "span_multi": {
                "match": {
                    "prefix": { "message": "alp" }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::SpanMulti {
                query: Box::new(Query::Prefix {
                    field: "message".to_string(),
                    value: "alp".to_string(),
                    case_insensitive: false,
                }),
            }
        );
    }

    #[test]
    fn parses_field_masking_span_queries() {
        let query = parse_query(&serde_json::json!({
            "field_masking_span": {
                "query": {
                    "span_term": { "message": "alpha" }
                },
                "field": "body"
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::FieldMaskingSpan {
                query: Box::new(Query::SpanTerm {
                    field: "message".to_string(),
                    value: serde_json::json!("alpha"),
                }),
                field: "body".to_string(),
            }
        );
    }

    #[test]
    fn parses_rank_feature_queries() {
        let query = parse_query(&serde_json::json!({
            "rank_feature": {
                "field": "priority"
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::RankFeature {
                field: "priority".to_string(),
            }
        );
    }

    #[test]
    fn parses_distance_feature_queries() {
        let query = parse_query(&serde_json::json!({
            "distance_feature": {
                "field": "published_at",
                "origin": "2025-01-01T00:00:00Z",
                "pivot": "7d"
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::DistanceFeature {
                field: "published_at".to_string(),
                origin: serde_json::json!("2025-01-01T00:00:00Z"),
                pivot: serde_json::json!("7d"),
            }
        );
    }

    #[test]
    fn parses_wrapper_queries() {
        let encoded = STANDARD.encode(r#"{"term":{"service":"api"}}"#);
        let query = parse_query(&serde_json::json!({
            "wrapper": {
                "query": encoded
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::Wrapper {
                query: Box::new(Query::Term {
                    field: "service".to_string(),
                    value: serde_json::json!("api"),
                }),
            }
        );
    }

    #[test]
    fn parses_nested_queries() {
        let query = parse_query(&serde_json::json!({
            "nested": {
                "path": "comments",
                "query": {
                    "term": { "author": "alice" }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::Nested {
                path: "comments".to_string(),
                query: Box::new(Query::Term {
                    field: "author".to_string(),
                    value: serde_json::json!("alice"),
                }),
            }
        );
    }

    #[test]
    fn parses_pinned_queries() {
        let query = parse_query(&serde_json::json!({
            "pinned": {
                "ids": ["1", "2"],
                "organic": {
                    "term": { "service": "api" }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::Pinned {
                ids: vec!["1".to_string(), "2".to_string()],
                organic: Box::new(Query::Term {
                    field: "service".to_string(),
                    value: serde_json::json!("api"),
                }),
            }
        );
    }

    #[test]
    fn parses_more_like_this_queries() {
        let query = parse_query(&serde_json::json!({
            "more_like_this": {
                "fields": ["title", "body"],
                "like": ["alpha beta", "gamma"]
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::MoreLikeThis {
                fields: Some(vec!["title".to_string(), "body".to_string()]),
                like: vec!["alpha beta".to_string(), "gamma".to_string()],
            }
        );
    }

    #[test]
    fn parses_constant_score_queries() {
        let query = parse_query(&serde_json::json!({
            "constant_score": {
                "filter": {
                    "term": { "service": "api" }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::ConstantScore {
                filter: Box::new(Query::Term {
                    field: "service".to_string(),
                    value: serde_json::json!("api"),
                }),
            }
        );
    }

    #[test]
    fn parses_dis_max_queries() {
        let query = parse_query(&serde_json::json!({
            "dis_max": {
                "queries": [
                    { "term": { "service": "api" } },
                    { "term": { "service": "worker" } }
                ],
                "tie_breaker": 0.1
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::DisMax {
                queries: vec![
                    Query::Term {
                        field: "service".to_string(),
                        value: serde_json::json!("api"),
                    },
                    Query::Term {
                        field: "service".to_string(),
                        value: serde_json::json!("worker"),
                    },
                ],
                tie_breaker: Some(0.1),
            }
        );
    }

    #[test]
    fn parses_boosting_queries() {
        let query = parse_query(&serde_json::json!({
            "boosting": {
                "positive": { "term": { "service": "api" } },
                "negative": { "term": { "service": "worker" } },
                "negative_boost": 0.2
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::Boosting {
                positive: Box::new(Query::Term {
                    field: "service".to_string(),
                    value: serde_json::json!("api"),
                }),
                negative: Box::new(Query::Term {
                    field: "service".to_string(),
                    value: serde_json::json!("worker"),
                }),
                negative_boost: 0.2,
            }
        );
    }

    #[test]
    fn parses_function_score_queries() {
        let query = parse_query(&serde_json::json!({
            "function_score": {
                "query": { "term": { "service": "api" } }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::FunctionScore {
                query: Box::new(Query::Term {
                    field: "service".to_string(),
                    value: serde_json::json!("api"),
                }),
            }
        );
    }

    #[test]
    fn parses_script_score_queries() {
        let query = parse_query(&serde_json::json!({
            "script_score": {
                "query": { "term": { "service": "api" } },
                "script": { "source": "_score" }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::ScriptScore {
                query: Box::new(Query::Term {
                    field: "service".to_string(),
                    value: serde_json::json!("api"),
                }),
                script: serde_json::json!({ "source": "_score" }),
            }
        );
    }

    #[test]
    fn parses_script_filter_queries() {
        let object_script = parse_query(&serde_json::json!({
            "script": {
                "script": {
                    "source": "doc['rank'].value > 1",
                    "lang": "painless"
                }
            }
        }))
        .unwrap();
        assert_eq!(
            object_script,
            Query::Script {
                script: serde_json::json!({
                    "source": "doc['rank'].value > 1",
                    "lang": "painless"
                }),
            }
        );

        let string_script = parse_query(&serde_json::json!({
            "script": {
                "script": "params._source['tenant'] == 'beta'",
                "_name": "tenant-script",
                "boost": 1.0
            }
        }))
        .unwrap();
        assert_eq!(
            string_script,
            Query::Script {
                script: serde_json::json!("params._source['tenant'] == 'beta'"),
            }
        );
    }

    #[test]
    fn parses_intervals_queries() {
        let query = parse_query(&serde_json::json!({
            "intervals": {
                "message": {
                    "all_of": {
                        "ordered": true,
                        "max_gaps": 0,
                        "intervals": [
                            { "match": { "query": "checkout" } },
                            { "match": { "query": "service" } }
                        ]
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::Intervals {
                field: "message".to_string(),
                spec: serde_json::json!({
                    "all_of": {
                        "ordered": true,
                        "max_gaps": 0,
                        "intervals": [
                            { "match": { "query": "checkout" } },
                            { "match": { "query": "service" } }
                        ]
                    }
                }),
            }
        );
    }

    #[test]
    fn parses_template_queries_as_rewritten_inner_query() {
        let query = parse_query(&serde_json::json!({
            "template": {
                "term": {
                    "message": {
                        "value": "foo"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::Term {
                field: "message".to_string(),
                value: serde_json::json!("foo"),
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
    fn parses_geo_distance_query() {
        let query = parse_query(&serde_json::json!({
            "geo_distance": {
                "distance": "2km",
                "ignore_unmapped": true,
                "location": {
                    "lat": 37.0,
                    "lon": -122.0
                }
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::GeoDistance(GeoDistanceQuery {
                field: "location".to_string(),
                distance_meters: 2000.0,
                lat: 37.0,
                lon: -122.0,
                ignore_unmapped: true,
            })
        );
    }

    #[test]
    fn parses_geo_bounding_box_query() {
        let query = parse_query(&serde_json::json!({
            "geo_bounding_box": {
                "location": {
                    "top_left": { "lat": 38.5, "lon": -122.5 },
                    "bottom_right": { "lat": 37.0, "lon": -121.0 }
                },
                "ignore_unmapped": true
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::GeoBoundingBox(GeoBoundingBoxQuery {
                field: "location".to_string(),
                top: 38.5,
                left: -122.5,
                bottom: 37.0,
                right: -121.0,
                ignore_unmapped: true,
            })
        );
    }

    #[test]
    fn parses_geo_polygon_query() {
        let query = parse_query(&serde_json::json!({
            "geo_polygon": {
                "location": {
                    "points": [
                        { "lat": 38.0, "lon": -123.0 },
                        [ -122.0, 38.0 ],
                        { "lat": 37.0, "lon": -122.0 }
                    ]
                },
                "ignore_unmapped": true
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::GeoPolygon(GeoPolygonQuery {
                field: "location".to_string(),
                points: vec![
                    GeoPoint {
                        lat: 38.0,
                        lon: -123.0
                    },
                    GeoPoint {
                        lat: 38.0,
                        lon: -122.0
                    },
                    GeoPoint {
                        lat: 37.0,
                        lon: -122.0
                    },
                    GeoPoint {
                        lat: 38.0,
                        lon: -123.0
                    },
                ],
                ignore_unmapped: true,
            })
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
    fn parses_range_aggregation_from_search_body() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "latency_ranges": {
                    "range": {
                        "field": "latency",
                        "ranges": [
                            { "to": 100.0 },
                            { "from": 100.0, "to": 200.0 },
                            { "key": "slow", "from": 200.0 }
                        ]
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations.get("latency_ranges"),
            Some(&Aggregation::Range(RangeAggregation {
                field: "latency".to_string(),
                ranges: vec![
                    RangeBucket {
                        key: None,
                        from: None,
                        to: Some(100.0)
                    },
                    RangeBucket {
                        key: None,
                        from: Some(100.0),
                        to: Some(200.0)
                    },
                    RangeBucket {
                        key: Some("slow".to_string()),
                        from: Some(200.0),
                        to: None
                    },
                ],
            }))
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
    fn parses_date_histogram_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "recent_events": {
                    "date_histogram": {
                        "field": "event_time",
                        "calendar_interval": "day"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["recent_events"],
            Aggregation::DateHistogram(DateHistogramAggregation {
                field: "event_time".to_string(),
                interval: "day".to_string(),
            })
        );
    }

    #[test]
    fn parses_fixed_interval_date_histogram_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "recent_events": {
                    "date_histogram": {
                        "field": "event_time",
                        "fixed_interval": "1h"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["recent_events"],
            Aggregation::DateHistogram(DateHistogramAggregation {
                field: "event_time".to_string(),
                interval: "1h".to_string(),
            })
        );
    }

    #[test]
    fn rejects_unsupported_date_histogram_options() {
        let error = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "recent_events": {
                    "date_histogram": {
                        "field": "event_time",
                        "calendar_interval": "day",
                        "min_doc_count": 0
                    }
                }
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedOption {
                clause: "date_histogram".to_string(),
                option: "min_doc_count".to_string()
            }
        );
    }

    #[test]
    fn parses_histogram_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "latency_histogram": {
                    "histogram": {
                        "field": "latency",
                        "interval": 10.0
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations.get("latency_histogram"),
            Some(&Aggregation::Histogram(HistogramAggregation {
                field: "latency".to_string(),
                interval: 10.0
            }))
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
            "weighted_latency": {
                "weighted_avg": {
                    "field": "latency",
                    "weight_field": "weight"
                }
            },
            "latency_boxplot": {
                "boxplot": {
                    "field": "latency"
                }
            },
            "latency_stats": {
                "stats": {
                    "field": "latency"
                    }
                },
                "latency_extended_stats": {
                    "extended_stats": {
                        "field": "latency"
                    }
                },
                "latency_percentiles": {
                    "percentiles": {
                        "field": "latency"
                    }
                },
                "latency_percentile_ranks": {
                    "percentile_ranks": {
                        "field": "latency",
                        "values": [10.0, 20.0]
                    }
                },
                "latency_median_absolute_deviation": {
                    "median_absolute_deviation": {
                        "field": "latency"
                    }
                },
                "service_cardinality": {
                    "cardinality": {
                        "field": "service"
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
                weight_field: None,
                values: None,
            })
        );
        assert_eq!(
            aggregations["avg_latency"],
            Aggregation::Metric(MetricAggregation {
                kind: MetricAggregationKind::Avg,
                field: "latency".to_string(),
                weight_field: None,
                values: None,
            })
        );
        assert_eq!(
            aggregations["weighted_latency"],
            Aggregation::Metric(MetricAggregation {
                kind: MetricAggregationKind::WeightedAvg,
                field: "latency".to_string(),
                weight_field: Some("weight".to_string()),
                values: None,
            })
        );
        assert_eq!(
            aggregations["latency_boxplot"],
            Aggregation::Metric(MetricAggregation {
                kind: MetricAggregationKind::Boxplot,
                field: "latency".to_string(),
                weight_field: None,
                values: None,
            })
        );
        assert_eq!(
            aggregations["latency_stats"],
            Aggregation::Metric(MetricAggregation {
                kind: MetricAggregationKind::Stats,
                field: "latency".to_string(),
                weight_field: None,
                values: None,
            })
        );
        assert_eq!(
            aggregations["latency_extended_stats"],
            Aggregation::Metric(MetricAggregation {
                kind: MetricAggregationKind::ExtendedStats,
                field: "latency".to_string(),
                weight_field: None,
                values: None,
            })
        );
        assert_eq!(
            aggregations["latency_percentiles"],
            Aggregation::Metric(MetricAggregation {
                kind: MetricAggregationKind::Percentiles,
                field: "latency".to_string(),
                weight_field: None,
                values: None,
            })
        );
        assert_eq!(
            aggregations["latency_percentile_ranks"],
            Aggregation::Metric(MetricAggregation {
                kind: MetricAggregationKind::PercentileRanks,
                field: "latency".to_string(),
                weight_field: None,
                values: Some(vec![10.0, 20.0]),
            })
        );
        assert_eq!(
            aggregations["latency_median_absolute_deviation"],
            Aggregation::Metric(MetricAggregation {
                kind: MetricAggregationKind::MedianAbsoluteDeviation,
                field: "latency".to_string(),
                weight_field: None,
                values: None,
            })
        );
        assert_eq!(
            aggregations["service_cardinality"],
            Aggregation::Metric(MetricAggregation {
                kind: MetricAggregationKind::Cardinality,
                field: "service".to_string(),
                weight_field: None,
                values: None,
            })
        );
        assert_eq!(
            aggregations["count_bytes"],
            Aggregation::Metric(MetricAggregation {
                kind: MetricAggregationKind::ValueCount,
                field: "bytes".to_string(),
                weight_field: None,
                values: None,
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
    fn parses_missing_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "missing_latency": {
                    "missing": {
                        "field": "latency"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["missing_latency"],
            Aggregation::Missing(MissingAggregation {
                field: "latency".to_string(),
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
    fn parses_top_hits_aggregation_sort_surface() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "recent": {
                    "top_hits": {
                        "from": 1,
                        "size": 2,
                        "sort": [
                            {
                                "timestamp": "desc"
                            }
                        ]
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["recent"],
            Aggregation::TopHits(TopHitsAggregation { from: 1, size: 2 })
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
    fn parses_geo_centroid_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "center": {
                    "geo_centroid": {
                        "field": "location"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["center"],
            Aggregation::GeoCentroid(GeoCentroidAggregation {
                field: "location".to_string()
            })
        );
    }

    #[test]
    fn parses_bucket_sort_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "service_bucket_sort": {
                    "bucket_sort": {
                        "aggregation": "by_service",
                        "sort": [
                            { "_count": "asc" },
                            { "_key": "asc" }
                        ],
                        "from": 1,
                        "size": 2
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["service_bucket_sort"],
            Aggregation::BucketSort(BucketSortAggregation {
                aggregation: "by_service".to_string(),
                sort: vec![
                    serde_json::json!({ "_count": "asc" }),
                    serde_json::json!({ "_key": "asc" })
                ],
                from: 1,
                size: 2
            })
        );
    }

    #[test]
    fn parses_bucket_script_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "service_bucket_script": {
                    "bucket_script": {
                        "aggregation": "by_service",
                        "path": "_count",
                        "script": "_value * params.scale",
                        "params": {
                            "scale": 2.0
                        }
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["service_bucket_script"],
            Aggregation::BucketScript(BucketScriptAggregation {
                aggregation: "by_service".to_string(),
                path: "_count".to_string(),
                script: "_value * params.scale".to_string(),
                params: [("scale".to_string(), serde_json::json!(2.0))]
                    .into_iter()
                    .collect()
            })
        );
    }

    #[test]
    fn parses_bucket_selector_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "service_bucket_selector": {
                    "bucket_selector": {
                        "aggregation": "by_service",
                        "path": "_count",
                        "op": "gt",
                        "value": 1.0
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["service_bucket_selector"],
            Aggregation::BucketSelector(BucketSelectorAggregation {
                aggregation: "by_service".to_string(),
                path: "_count".to_string(),
                op: "gt".to_string(),
                value: 1.0
            })
        );
    }

    #[test]
    fn parses_bucket_count_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "service_bucket_count": {
                    "bucket_count": {
                        "aggregation": "by_service"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["service_bucket_count"],
            Aggregation::BucketCount(BucketCountAggregation {
                aggregation: "by_service".to_string()
            })
        );
    }

    #[test]
    fn parses_normalize_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "service_normalize": {
                    "normalize": {
                        "aggregation": "by_service",
                        "path": "_count"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["service_normalize"],
            Aggregation::Normalize(NormalizeAggregation {
                aggregation: "by_service".to_string(),
                path: "_count".to_string()
            })
        );
    }

    #[test]
    fn rejects_unsupported_geo_centroid_options() {
        let error = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "center": {
                    "geo_centroid": {
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
                clause: "geo_centroid".to_string(),
                option: "wrap_longitude".to_string(),
            }
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
                buckets_path: "by_service>_count".to_string(),
                window: None,
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_avg_bucket_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "average_services": {
                    "avg_bucket": {
                        "buckets_path": "by_service>_count"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["average_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::AvgBucket,
                buckets_path: "by_service>_count".to_string(),
                window: None,
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_min_and_max_bucket_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "min_services": {
                    "min_bucket": {
                        "buckets_path": "by_service>_count"
                    }
                },
                "max_services": {
                    "max_bucket": {
                        "buckets_path": "by_service>_count"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["min_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::MinBucket,
                buckets_path: "by_service>_count".to_string(),
                window: None,
                percents: None,
                values: None,
            })
        );
        assert_eq!(
            aggregations["max_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::MaxBucket,
                buckets_path: "by_service>_count".to_string(),
                window: None,
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_moving_avg_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "moving_average_services": {
                    "moving_avg": {
                        "buckets_path": "by_service>_count",
                        "window": 2
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["moving_average_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::MovingAvg,
                buckets_path: "by_service>_count".to_string(),
                window: Some(2),
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_moving_count_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "moving_count_services": {
                    "moving_count": {
                        "buckets_path": "by_service>_count",
                        "window": 3
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["moving_count_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::MovingCount,
                buckets_path: "by_service>_count".to_string(),
                window: Some(3),
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_moving_sum_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "moving_sum_services": {
                    "moving_sum": {
                        "buckets_path": "by_service>_count",
                        "window": 2
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["moving_sum_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::MovingSum,
                buckets_path: "by_service>_count".to_string(),
                window: Some(2),
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_moving_min_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "moving_min_services": {
                    "moving_min": {
                        "buckets_path": "by_service>_count",
                        "window": 2
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["moving_min_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::MovingMin,
                buckets_path: "by_service>_count".to_string(),
                window: Some(2),
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_moving_max_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "moving_max_services": {
                    "moving_max": {
                        "buckets_path": "by_service>_count",
                        "window": 2
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["moving_max_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::MovingMax,
                buckets_path: "by_service>_count".to_string(),
                window: Some(2),
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_moving_median_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "moving_median_services": {
                    "moving_median": {
                        "buckets_path": "by_service>_count",
                        "window": 2
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["moving_median_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::MovingMedian,
                buckets_path: "by_service>_count".to_string(),
                window: Some(2),
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_moving_stddev_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "moving_stddev_services": {
                    "moving_stddev": {
                        "buckets_path": "by_service>_count",
                        "window": 2
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["moving_stddev_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::MovingStddev,
                buckets_path: "by_service>_count".to_string(),
                window: Some(2),
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_moving_variance_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "moving_variance_services": {
                    "moving_variance": {
                        "buckets_path": "by_service>_count",
                        "window": 2
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["moving_variance_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::MovingVariance,
                buckets_path: "by_service>_count".to_string(),
                window: Some(2),
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_moving_skewness_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "moving_skewness_services": {
                    "moving_skewness": {
                        "buckets_path": "by_service>_count",
                        "window": 2
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["moving_skewness_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::MovingSkewness,
                buckets_path: "by_service>_count".to_string(),
                window: Some(2),
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_moving_kurtosis_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "moving_kurtosis_services": {
                    "moving_kurtosis": {
                        "buckets_path": "by_service>_count",
                        "window": 2
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["moving_kurtosis_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::MovingKurtosis,
                buckets_path: "by_service>_count".to_string(),
                window: Some(2),
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_moving_mad_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "moving_mad_services": {
                    "moving_mad": {
                        "buckets_path": "by_service>_count",
                        "window": 2
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["moving_mad_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::MovingMad,
                buckets_path: "by_service>_count".to_string(),
                window: Some(2),
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_moving_range_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "moving_range_services": {
                    "moving_range": {
                        "buckets_path": "by_service>_count",
                        "window": 2
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["moving_range_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::MovingRange,
                buckets_path: "by_service>_count".to_string(),
                window: Some(2),
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_moving_percentiles_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "moving_percentiles_services": {
                    "moving_percentiles": {
                        "buckets_path": "by_service>_count",
                        "window": 2,
                        "percents": [50.0, 100.0]
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["moving_percentiles_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::MovingPercentiles,
                buckets_path: "by_service>_count".to_string(),
                window: Some(2),
                percents: Some(vec![50.0, 100.0]),
                values: None,
            })
        );
    }

    #[test]
    fn parses_moving_percentile_ranks_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "moving_percentile_ranks_services": {
                    "moving_percentile_ranks": {
                        "buckets_path": "by_service>_count",
                        "window": 2,
                        "values": [2.0, 3.0]
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["moving_percentile_ranks_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::MovingPercentileRanks,
                buckets_path: "by_service>_count".to_string(),
                window: Some(2),
                percents: None,
                values: Some(vec![2.0, 3.0]),
            })
        );
    }

    #[test]
    fn parses_cumulative_sum_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "running_services": {
                    "cumulative_sum": {
                        "buckets_path": "by_service>_count"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["running_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::CumulativeSum,
                buckets_path: "by_service>_count".to_string(),
                window: None,
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_percentile_ranks_bucket_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "service_percentile_ranks": {
                    "percentile_ranks_bucket": {
                        "buckets_path": "by_service>latency_sum",
                        "values": [5.0, 30.0]
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["service_percentile_ranks"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::PercentileRanksBucket,
                buckets_path: "by_service>latency_sum".to_string(),
                window: None,
                percents: None,
                values: Some(vec![5.0, 30.0]),
            })
        );
    }

    #[test]
    fn parses_serial_diff_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "service_delta": {
                    "serial_diff": {
                        "buckets_path": "by_service>_count",
                        "lag": 2
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["service_delta"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::SerialDiff,
                buckets_path: "by_service>_count".to_string(),
                window: Some(2),
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_derivative_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "service_derivative": {
                    "derivative": {
                        "buckets_path": "by_service>_count"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["service_derivative"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::Derivative,
                buckets_path: "by_service>_count".to_string(),
                window: None,
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_stats_bucket_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "stats_services": {
                    "stats_bucket": {
                        "buckets_path": "by_service>_count"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["stats_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::StatsBucket,
                buckets_path: "by_service>_count".to_string(),
                window: None,
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_extended_stats_bucket_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "extended_stats_services": {
                    "extended_stats_bucket": {
                        "buckets_path": "by_service>_count"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["extended_stats_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::ExtendedStatsBucket,
                buckets_path: "by_service>_count".to_string(),
                window: None,
                percents: None,
                values: None,
            })
        );
    }

    #[test]
    fn parses_percentiles_bucket_pipeline_aggregation() {
        let aggregations = parse_search_aggregations(&serde_json::json!({
            "aggs": {
                "percentiles_services": {
                    "percentiles_bucket": {
                        "buckets_path": "by_service>_count"
                    }
                }
            }
        }))
        .unwrap();

        assert_eq!(
            aggregations["percentiles_services"],
            Aggregation::Pipeline(PipelineAggregation {
                kind: PipelineAggregationKind::PercentilesBucket,
                buckets_path: "by_service>_count".to_string(),
                window: None,
                percents: None,
                values: None,
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
                weight_field: None,
                values: None,
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
    fn rejects_weighted_avg_without_weight_field() {
        let error = parse_aggregation_map(&serde_json::json!({
            "latency_weighted_avg": {
                "weighted_avg": {
                    "field": "latency_ms"
                }
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::MissingField {
                clause: "weighted_avg".to_string(),
                field: "weight_field".to_string(),
            }
        );
    }

    #[test]
    fn rejects_percentile_ranks_without_values() {
        let error = parse_aggregation_map(&serde_json::json!({
            "latency_percentile_ranks": {
                "percentile_ranks": {
                    "field": "latency_ms"
                }
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::MissingField {
                clause: "percentile_ranks".to_string(),
                field: "values".to_string(),
            }
        );
    }

    #[test]
    fn rejects_unsupported_query_clause() {
        let error = parse_query(&serde_json::json!({
            "percolate": {}
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedClause {
                clause: "percolate".to_string()
            }
        );
    }

    #[test]
    fn parses_geo_shape_point_queries() {
        let query = parse_query(&serde_json::json!({
            "geo_shape": {
                "shape": {
                    "shape": {
                        "type": "point",
                        "coordinates": [10.0, 20.0]
                    },
                    "relation": "intersects"
                },
                "ignore_unmapped": true
            }
        }))
        .unwrap();

        assert_eq!(
            query,
            Query::GeoShape(GeoShapeQuery {
                field: "shape".to_string(),
                shape: serde_json::json!({
                    "type": "point",
                    "coordinates": [10.0, 20.0]
                }),
                relation: "intersects".to_string(),
                ignore_unmapped: true
            })
        );
    }

    #[test]
    fn rejects_geo_shape_indexed_shape_subset() {
        let error = parse_query(&serde_json::json!({
            "geo_shape": {
                "shape": {
                    "indexed_shape": {
                        "id": "shape-1"
                    }
                }
            }
        }))
        .unwrap_err();

        assert_eq!(
            error,
            QueryDslError::UnsupportedOption {
                clause: "geo_shape".to_string(),
                option: "indexed_shape".to_string()
            }
        );
    }
}
