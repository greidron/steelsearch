//! Engine abstraction for Lucene-compatible and Rust-native backends.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::cmp::Ordering;
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use thiserror::Error;

pub type EngineResult<T> = std::result::Result<T, EngineError>;

pub const SHARD_MANIFEST_FILE_NAME: &str = "steelsearch-shard-manifest.json";

#[derive(Clone, Debug, Eq, Error, PartialEq)]
pub enum EngineError {
    #[error("index [{index}] already exists")]
    IndexAlreadyExists { index: String },
    #[error("no such index [{index}]")]
    IndexNotFound { index: String },
    #[error("document [{id}] missing in index [{index}]")]
    DocumentNotFound { index: String, id: String },
    #[error("version conflict: {reason}")]
    VersionConflict { reason: String },
    #[error("invalid engine request: {reason}")]
    InvalidRequest { reason: String },
    #[error("engine backend failure: {reason}")]
    BackendFailure { reason: String },
}

impl EngineError {
    pub fn status_code(&self) -> u16 {
        match self {
            Self::IndexAlreadyExists { .. } | Self::InvalidRequest { .. } => 400,
            Self::IndexNotFound { .. } | Self::DocumentNotFound { .. } => 404,
            Self::VersionConflict { .. } => 409,
            Self::BackendFailure { .. } => 500,
        }
    }

    pub fn opensearch_error_type(&self) -> &'static str {
        match self {
            Self::IndexAlreadyExists { .. } => "resource_already_exists_exception",
            Self::IndexNotFound { .. } => "index_not_found_exception",
            Self::DocumentNotFound { .. } => "document_missing_exception",
            Self::VersionConflict { .. } => "version_conflict_engine_exception",
            Self::InvalidRequest { .. } => "illegal_argument_exception",
            Self::BackendFailure { .. } => "engine_exception",
        }
    }

    pub fn opensearch_reason(&self) -> String {
        self.to_string()
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CreateIndexRequest {
    pub index: String,
    pub settings: Value,
    pub mappings: Value,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ShardManifest {
    pub index_uuid: String,
    pub shard_id: u32,
    pub allocation_id: String,
    pub primary_term: u64,
    pub max_sequence_number: i64,
    pub local_checkpoint: i64,
    #[serde(default = "default_unset_sequence_number")]
    pub refreshed_sequence_number: i64,
    pub committed_generation: u64,
    pub translog_generation: u64,
    pub schema_hash: u64,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub vector_segments: Vec<VectorSegmentMetadata>,
}

impl ShardManifest {
    pub fn manifest_path(shard_path: impl AsRef<Path>) -> PathBuf {
        shard_path.as_ref().join(SHARD_MANIFEST_FILE_NAME)
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct VectorSegmentMetadata {
    pub field: String,
    pub dimension: usize,
    pub document_count: usize,
    pub vector_count: usize,
    pub vector_format: String,
    pub ann_graph: Option<String>,
}

pub fn persist_shard_manifest(
    shard_path: impl AsRef<Path>,
    manifest: &ShardManifest,
) -> EngineResult<()> {
    let shard_path = shard_path.as_ref();
    fs::create_dir_all(shard_path).map_err(|error| EngineError::BackendFailure {
        reason: format!(
            "failed to create shard path [{}]: {error}",
            shard_path.display()
        ),
    })?;

    let manifest_path = ShardManifest::manifest_path(shard_path);
    let temp_path = manifest_path.with_extension("json.tmp");
    let file = ShardManifestFile {
        manifest: manifest.clone(),
        checksum: shard_manifest_checksum(manifest)?,
    };
    let bytes = serde_json::to_vec_pretty(&file).map_err(|error| EngineError::BackendFailure {
        reason: format!("failed to serialize shard manifest: {error}"),
    })?;

    fs::write(&temp_path, bytes).map_err(|error| EngineError::BackendFailure {
        reason: format!(
            "failed to write shard manifest temp file [{}]: {error}",
            temp_path.display()
        ),
    })?;
    fs::rename(&temp_path, &manifest_path).map_err(|error| EngineError::BackendFailure {
        reason: format!(
            "failed to commit shard manifest [{}]: {error}",
            manifest_path.display()
        ),
    })
}

pub fn load_shard_manifest(shard_path: impl AsRef<Path>) -> EngineResult<ShardManifest> {
    let manifest_path = ShardManifest::manifest_path(shard_path);
    let bytes = fs::read(&manifest_path).map_err(|error| EngineError::BackendFailure {
        reason: format!(
            "failed to read shard manifest [{}]: {error}",
            manifest_path.display()
        ),
    })?;
    let file = serde_json::from_slice::<ShardManifestFile>(&bytes).map_err(|error| {
        EngineError::BackendFailure {
            reason: format!(
                "failed to parse shard manifest [{}]: {error}",
                manifest_path.display()
            ),
        }
    })?;
    let actual = shard_manifest_checksum(&file.manifest)?;
    if actual != file.checksum {
        return Err(EngineError::BackendFailure {
            reason: format!(
                "shard manifest checksum mismatch [{}]: expected {}, got {}",
                manifest_path.display(),
                file.checksum,
                actual
            ),
        });
    }
    Ok(file.manifest)
}

pub fn shard_manifest_checksum(manifest: &ShardManifest) -> EngineResult<u64> {
    let bytes = serde_json::to_vec(manifest).map_err(|error| EngineError::BackendFailure {
        reason: format!("failed to serialize shard manifest for checksum: {error}"),
    })?;
    Ok(stable_hash64(&bytes))
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
struct ShardManifestFile {
    manifest: ShardManifest,
    checksum: u64,
}

fn default_unset_sequence_number() -> i64 {
    -1
}

fn stable_hash64(bytes: &[u8]) -> u64 {
    let mut hash = 0xcbf29ce484222325_u64;
    for byte in bytes {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x100000001b3);
    }
    hash
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CreateIndexResponse {
    pub index: String,
    pub acknowledged: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexDocumentRequest {
    pub index: String,
    #[serde(rename = "_id")]
    pub id: String,
    #[serde(rename = "_source")]
    pub source: Value,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ReplayDocumentRequest {
    pub index: String,
    pub metadata: DocumentMetadata,
    #[serde(default)]
    pub coordination: WriteCoordinationMetadata,
    #[serde(rename = "_source")]
    pub source: Value,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DeleteDocumentRequest {
    pub index: String,
    #[serde(rename = "_id")]
    pub id: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct UpdateDocumentRequest {
    pub index: String,
    #[serde(rename = "_id")]
    pub id: String,
    pub doc: Value,
    #[serde(default)]
    pub doc_as_upsert: bool,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct WriteCondition {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub if_seq_no: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub if_primary_term: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub version: Option<u64>,
    #[serde(default)]
    pub version_type: VersionType,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum VersionType {
    #[default]
    Internal,
    External,
    ExternalGte,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ConditionalIndexDocumentRequest {
    pub request: IndexDocumentRequest,
    #[serde(default)]
    pub condition: WriteCondition,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ConditionalUpdateDocumentRequest {
    pub request: UpdateDocumentRequest,
    #[serde(default)]
    pub condition: WriteCondition,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ConditionalDeleteDocumentRequest {
    pub request: DeleteDocumentRequest,
    #[serde(default)]
    pub condition: WriteCondition,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct BulkWriteRequest {
    pub operations: Vec<BulkWriteOperation>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case", tag = "operation", content = "request")]
pub enum BulkWriteOperation {
    Index(IndexDocumentRequest),
    Create(IndexDocumentRequest),
    Update(UpdateDocumentRequest),
    Delete(DeleteDocumentRequest),
    Replay(ReplayDocumentRequest),
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct BulkWriteResponse {
    pub errors: bool,
    pub items: Vec<BulkWriteItemResponse>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct BulkWriteItemResponse {
    pub operation: WriteOperationKind,
    pub index: String,
    #[serde(rename = "_id")]
    pub id: String,
    pub status: u16,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<WriteResult>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<DocumentMetadata>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub coordination: Option<WriteCoordinationMetadata>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error_type: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexDocumentResponse {
    pub index: String,
    pub metadata: DocumentMetadata,
    pub coordination: WriteCoordinationMetadata,
    pub result: WriteResult,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DocumentMetadata {
    #[serde(rename = "_id")]
    pub id: String,
    #[serde(rename = "_version")]
    pub version: u64,
    #[serde(rename = "_seq_no")]
    pub seq_no: i64,
    #[serde(rename = "_primary_term")]
    pub primary_term: u64,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct WriteCoordinationMetadata {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub translog_location: Option<TranslogLocation>,
    #[serde(default = "default_unset_sequence_number")]
    pub global_checkpoint: i64,
    #[serde(default = "default_unset_sequence_number")]
    pub local_checkpoint: i64,
    #[serde(default)]
    pub retention_leases: Vec<RetentionLease>,
    #[serde(default)]
    pub noop: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct TranslogLocation {
    pub generation: u64,
    pub offset: u64,
    pub size: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RetentionLease {
    pub id: String,
    pub retaining_sequence_number: i64,
    pub source: String,
    pub timestamp_millis: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WriteResult {
    Created,
    Updated,
    Deleted,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WriteOperationKind {
    Index,
    Create,
    Update,
    Delete,
    Replay,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RefreshPolicy {
    #[default]
    None,
    Immediate,
    WaitFor,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct GetDocumentRequest {
    pub index: String,
    #[serde(rename = "_id")]
    pub id: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct GetDocumentResponse {
    pub index: String,
    pub metadata: DocumentMetadata,
    #[serde(rename = "_source")]
    pub source: Value,
    pub found: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RefreshRequest {
    pub indices: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RefreshResponse {
    pub refreshed: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct SearchRequest {
    pub indices: Vec<String>,
    pub query: Value,
    pub aggregations: Value,
    pub sort: Vec<SortSpec>,
    pub from: usize,
    pub size: usize,
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SearchMemoryReservation {
    pub doc_values_bytes: usize,
    pub vector_bytes: usize,
    pub transport_bytes: usize,
}

impl SearchMemoryReservation {
    pub fn total_bytes(self) -> usize {
        self.doc_values_bytes
            .saturating_add(self.vector_bytes)
            .saturating_add(self.transport_bytes)
    }
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SearchMemoryUsageCounters {
    pub doc_values_bytes: usize,
    pub vector_bytes: usize,
    pub collector_bytes: usize,
    pub request_result_cache_bytes: usize,
    pub vector_graph_cache_bytes: usize,
    pub fast_field_cache_bytes: usize,
    pub cache_bytes: usize,
    pub transport_bytes: usize,
}

impl SearchMemoryUsageCounters {
    pub fn total_bytes(self) -> usize {
        self.doc_values_bytes
            .saturating_add(self.vector_bytes)
            .saturating_add(self.collector_bytes)
            .saturating_add(self.cache_bytes)
            .saturating_add(self.transport_bytes)
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SearchCacheTelemetrySnapshot {
    pub request_result_cache_bytes: usize,
    pub request_result_cache_entries: usize,
    pub request_result_cache_hits: u64,
    pub request_result_cache_misses: u64,
    pub request_result_cache_evictions: u64,
    pub request_result_cache_capacity_evictions: u64,
    pub request_result_cache_resets: u64,
    pub request_result_cache_invalidated_entries: u64,
    pub request_result_cache_refresh_invalidations: u64,
    pub request_result_cache_stale_invalidations: u64,
    pub vector_graph_cache_bytes: usize,
    pub vector_graph_cache_entries: usize,
    pub vector_graph_cache_hits: u64,
    pub vector_graph_cache_misses: u64,
    pub vector_graph_cache_evictions: u64,
    pub vector_graph_cache_capacity_evictions: u64,
    pub vector_graph_cache_resets: u64,
    pub vector_graph_cache_invalidated_entries: u64,
    pub vector_graph_cache_refresh_invalidations: u64,
    pub vector_graph_cache_stale_invalidations: u64,
    pub fast_field_cache_bytes: usize,
    pub fast_field_cache_entries: usize,
    pub fast_field_cache_hits: u64,
    pub fast_field_cache_misses: u64,
    pub fast_field_cache_evictions: u64,
    pub fast_field_cache_capacity_evictions: u64,
    pub fast_field_cache_resets: u64,
    pub fast_field_cache_invalidated_entries: u64,
    pub fast_field_cache_refresh_invalidations: u64,
    pub fast_field_cache_stale_invalidations: u64,
}

impl SearchCacheTelemetrySnapshot {
    pub fn total_bytes(&self) -> usize {
        self.request_result_cache_bytes
            .saturating_add(self.vector_graph_cache_bytes)
            .saturating_add(self.fast_field_cache_bytes)
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SearchCacheIndexTelemetrySnapshot {
    pub summary: SearchCacheTelemetrySnapshot,
    pub request_result_cache_oldest_entry_age_ticks: u64,
    pub request_result_cache_newest_entry_age_ticks: u64,
    pub vector_graph_cache_oldest_entry_age_ticks: u64,
    pub vector_graph_cache_newest_entry_age_ticks: u64,
    pub fast_field_cache_oldest_entry_age_ticks: u64,
    pub fast_field_cache_newest_entry_age_ticks: u64,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub request_result_cache_fields: BTreeMap<String, SearchCacheFieldTelemetrySnapshot>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub vector_graph_cache_fields: BTreeMap<String, SearchCacheFieldTelemetrySnapshot>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub fast_field_cache_fields: BTreeMap<String, SearchCacheFieldTelemetrySnapshot>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SearchCacheFieldTelemetrySnapshot {
    pub request_result_cache_bytes: usize,
    pub request_result_cache_entries: usize,
    pub request_result_cache_hits: u64,
    pub request_result_cache_misses: u64,
    pub request_result_cache_evictions: u64,
    pub request_result_cache_capacity_evictions: u64,
    pub request_result_cache_resets: u64,
    pub request_result_cache_invalidated_entries: u64,
    pub request_result_cache_refresh_invalidations: u64,
    pub request_result_cache_stale_invalidations: u64,
    pub request_result_cache_oldest_entry_age_ticks: u64,
    pub request_result_cache_newest_entry_age_ticks: u64,
    pub vector_graph_cache_bytes: usize,
    pub vector_graph_cache_entries: usize,
    pub vector_graph_cache_hits: u64,
    pub vector_graph_cache_misses: u64,
    pub vector_graph_cache_evictions: u64,
    pub vector_graph_cache_capacity_evictions: u64,
    pub vector_graph_cache_resets: u64,
    pub vector_graph_cache_invalidated_entries: u64,
    pub vector_graph_cache_refresh_invalidations: u64,
    pub vector_graph_cache_stale_invalidations: u64,
    pub vector_graph_cache_oldest_entry_age_ticks: u64,
    pub vector_graph_cache_newest_entry_age_ticks: u64,
    pub fast_field_cache_bytes: usize,
    pub fast_field_cache_entries: usize,
    pub fast_field_cache_hits: u64,
    pub fast_field_cache_misses: u64,
    pub fast_field_cache_evictions: u64,
    pub fast_field_cache_capacity_evictions: u64,
    pub fast_field_cache_resets: u64,
    pub fast_field_cache_invalidated_entries: u64,
    pub fast_field_cache_refresh_invalidations: u64,
    pub fast_field_cache_stale_invalidations: u64,
    pub fast_field_cache_oldest_entry_age_ticks: u64,
    pub fast_field_cache_newest_entry_age_ticks: u64,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SearchCacheTelemetryDetails {
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub indices: BTreeMap<String, SearchCacheIndexTelemetrySnapshot>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SortSpec {
    pub field: String,
    #[serde(default)]
    pub order: SortOrder,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SortOrder {
    #[default]
    Asc,
    Desc,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct SearchResponse {
    pub total_hits: u64,
    pub hits: Vec<SearchHit>,
    pub aggregations: Value,
    #[serde(default)]
    pub shards: SearchShardStats,
    #[serde(default)]
    pub phase_results: Vec<SearchPhaseResult>,
    #[serde(default)]
    pub fetch_subphases: Vec<SearchFetchSubphaseResult>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub profile: Option<SearchProfile>,
}

impl SearchResponse {
    pub fn new(total_hits: u64, hits: Vec<SearchHit>, aggregations: Value) -> Self {
        Self {
            total_hits,
            hits,
            aggregations,
            shards: SearchShardStats::single_success(),
            phase_results: Vec::new(),
            fetch_subphases: Vec::new(),
            profile: None,
        }
    }

    pub fn with_phase_results(mut self, phase_results: Vec<SearchPhaseResult>) -> Self {
        self.phase_results = phase_results;
        self
    }

    pub fn with_fetch_subphases(mut self, fetch_subphases: Vec<SearchFetchSubphaseResult>) -> Self {
        self.fetch_subphases = fetch_subphases;
        self
    }

    pub fn with_shards(mut self, shards: SearchShardStats) -> Self {
        self.shards = shards;
        self
    }

    pub fn with_profile(mut self, profile: SearchProfile) -> Self {
        self.profile = Some(profile);
        self
    }

    pub fn to_opensearch_body(&self, took_millis: u64) -> Value {
        let max_score = self
            .hits
            .iter()
            .map(|hit| hit.score)
            .reduce(f32::max)
            .map(Value::from)
            .unwrap_or(Value::Null);

        let mut body = serde_json::json!({
            "took": took_millis,
            "timed_out": false,
            "_shards": self.shards.to_opensearch_body(),
            "hits": {
                "total": {
                    "value": self.total_hits,
                    "relation": "eq"
                },
                "max_score": max_score,
                "hits": self
                    .hits
                    .iter()
                    .map(SearchHit::to_opensearch_body)
                    .collect::<Vec<_>>()
            }
        });

        if self
            .aggregations
            .as_object()
            .is_some_and(|aggregations| !aggregations.is_empty())
        {
            body["aggregations"] = self.aggregations.clone();
        }

        if let Some(profile) = &self.profile {
            body["profile"] = profile.to_opensearch_body();
        }

        body
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SearchShardStats {
    pub total: u64,
    pub successful: u64,
    pub skipped: u64,
    pub failed: u64,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub failures: Vec<SearchShardFailure>,
}

impl SearchShardStats {
    pub fn single_success() -> Self {
        Self {
            total: 1,
            successful: 1,
            skipped: 0,
            failed: 0,
            failures: Vec::new(),
        }
    }

    pub fn to_opensearch_body(&self) -> Value {
        let mut body = serde_json::json!({
            "total": self.total,
            "successful": self.successful,
            "skipped": self.skipped,
            "failed": self.failed
        });
        if !self.failures.is_empty() {
            body["failures"] = Value::Array(
                self.failures
                    .iter()
                    .map(SearchShardFailure::to_opensearch_body)
                    .collect(),
            );
        }
        body
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SearchShardFailure {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub index: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub shard: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub node: Option<String>,
    pub reason: String,
    pub status: u16,
}

impl SearchShardFailure {
    pub fn to_opensearch_body(&self) -> Value {
        let mut body = serde_json::json!({
            "reason": {
                "type": "search_phase_execution_exception",
                "reason": self.reason
            },
            "status": self.status
        });
        if let Some(index) = &self.index {
            body["index"] = Value::from(index.clone());
        }
        if let Some(shard) = self.shard {
            body["shard"] = Value::from(shard);
        }
        if let Some(node) = &self.node {
            body["node"] = Value::from(node.clone());
        }
        body
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SearchPhase {
    CanMatch,
    Dfs,
    Query,
    Fetch,
    Highlight,
    Explain,
    Profile,
    Collapse,
    Rescore,
    SearchAfter,
    Scroll,
    PointInTime,
    Slice,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SearchPhaseResult {
    pub phase: SearchPhase,
    pub took_millis: u64,
    pub skipped: bool,
    pub description: String,
}

impl SearchPhaseResult {
    pub fn completed(phase: SearchPhase, description: impl Into<String>) -> Self {
        Self {
            phase,
            took_millis: 0,
            skipped: false,
            description: description.into(),
        }
    }

    pub fn skipped(phase: SearchPhase, description: impl Into<String>) -> Self {
        Self {
            phase,
            took_millis: 0,
            skipped: true,
            description: description.into(),
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SearchProfile {
    pub phases: Vec<SearchPhaseResult>,
    #[serde(default)]
    pub fetch_subphases: Vec<SearchFetchSubphaseResult>,
}

impl SearchProfile {
    pub fn from_phases(phases: Vec<SearchPhaseResult>) -> Self {
        Self {
            phases,
            fetch_subphases: Vec::new(),
        }
    }

    pub fn with_fetch_subphases(mut self, fetch_subphases: Vec<SearchFetchSubphaseResult>) -> Self {
        self.fetch_subphases = fetch_subphases;
        self
    }

    pub fn to_opensearch_body(&self) -> Value {
        serde_json::json!({
            "shards": [
                {
                    "id": "[steelsearch][0]",
                    "searches": [
                        {
                            "query": self.phases.iter().map(|phase| {
                                serde_json::json!({
                                    "type": format!("{:?}", phase.phase),
                                    "description": phase.description,
                                    "time_in_nanos": phase.took_millis.saturating_mul(1_000_000),
                                    "breakdown": {}
                                })
                            }).collect::<Vec<_>>(),
                            "fetch": {
                                "type": "fetch",
                                "description": "fetch subphases",
                                "time_in_nanos": self.fetch_subphases.iter()
                                    .map(|subphase| subphase.took_millis.saturating_mul(1_000_000))
                                    .sum::<u64>(),
                                "breakdown": {},
                                "children": self.fetch_subphases.iter().map(|subphase| {
                                    serde_json::json!({
                                        "type": format!("{:?}", subphase.subphase),
                                        "description": subphase.description,
                                        "time_in_nanos": subphase.took_millis.saturating_mul(1_000_000),
                                        "breakdown": {},
                                        "skipped": subphase.skipped
                                    })
                                }).collect::<Vec<_>>()
                            }
                        }
                    ]
                }
            ]
        })
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SearchFetchSubphase {
    Source,
    Version,
    SeqNoPrimaryTerm,
    StoredFields,
    Highlight,
    Explain,
    ScriptFields,
    InnerHits,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SearchFetchSubphaseResult {
    pub subphase: SearchFetchSubphase,
    pub took_millis: u64,
    pub skipped: bool,
    pub description: String,
}

impl SearchFetchSubphaseResult {
    pub fn completed(subphase: SearchFetchSubphase, description: impl Into<String>) -> Self {
        Self {
            subphase,
            took_millis: 0,
            skipped: false,
            description: description.into(),
        }
    }

    pub fn skipped(subphase: SearchFetchSubphase, description: impl Into<String>) -> Self {
        Self {
            subphase,
            took_millis: 0,
            skipped: true,
            description: description.into(),
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SearchShardTarget {
    pub index: String,
    pub shard: u32,
    pub node: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct SearchShardSearchResult {
    pub target: SearchShardTarget,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub response: Option<SearchResponse>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub failure: Option<SearchShardFailure>,
}

impl SearchShardSearchResult {
    pub fn success(target: SearchShardTarget, response: SearchResponse) -> Self {
        Self {
            target,
            response: Some(response),
            failure: None,
        }
    }

    pub fn failure(target: SearchShardTarget, reason: impl Into<String>, status: u16) -> Self {
        let failure = SearchShardFailure {
            index: Some(target.index.clone()),
            shard: Some(target.shard),
            node: Some(target.node.clone()),
            reason: reason.into(),
            status,
        };
        Self {
            target,
            response: None,
            failure: Some(failure),
        }
    }
}

pub fn merge_shard_search_results(
    shard_results: Vec<SearchShardSearchResult>,
    from: usize,
    size: usize,
) -> SearchResponse {
    let mut total_hits = 0;
    let mut hits = Vec::new();
    let mut phase_results = Vec::new();
    let mut fetch_subphases = Vec::new();
    let mut failures = Vec::new();
    let total = shard_results.len() as u64;
    let mut successful = 0;

    for shard_result in shard_results {
        if let Some(response) = shard_result.response {
            successful += 1;
            total_hits += response.total_hits;
            hits.extend(response.hits);
            phase_results.extend(response.phase_results);
            fetch_subphases.extend(response.fetch_subphases);
        } else if let Some(failure) = shard_result.failure {
            failures.push(failure);
        }
    }

    hits.sort_by(|left, right| {
        right
            .score
            .partial_cmp(&left.score)
            .unwrap_or(Ordering::Equal)
            .then_with(|| left.index.cmp(&right.index))
            .then_with(|| left.metadata.id.cmp(&right.metadata.id))
    });
    let hits = hits.into_iter().skip(from).take(size).collect();
    let failed = failures.len() as u64;

    SearchResponse::new(total_hits, hits, serde_json::json!({}))
        .with_shards(SearchShardStats {
            total,
            successful,
            skipped: 0,
            failed,
            failures,
        })
        .with_phase_results(phase_results)
        .with_fetch_subphases(fetch_subphases)
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct SearchHit {
    pub index: String,
    pub metadata: DocumentMetadata,
    pub score: f32,
    #[serde(rename = "_source")]
    pub source: Value,
}

impl SearchHit {
    pub fn to_opensearch_body(&self) -> Value {
        serde_json::json!({
            "_index": self.index,
            "_id": self.metadata.id,
            "_score": self.score,
            "_source": self.source,
            "_version": self.metadata.version,
            "_seq_no": self.metadata.seq_no,
            "_primary_term": self.metadata.primary_term
        })
    }
}

pub trait IndexEngine: Send + Sync {
    fn create_index(&self, request: CreateIndexRequest) -> EngineResult<CreateIndexResponse>;
    fn index_document(&self, request: IndexDocumentRequest) -> EngineResult<IndexDocumentResponse>;
    fn index_document_with_refresh(
        &self,
        request: IndexDocumentRequest,
        refresh_policy: RefreshPolicy,
    ) -> EngineResult<IndexDocumentResponse> {
        match refresh_policy {
            RefreshPolicy::None => self.index_document(request),
            RefreshPolicy::Immediate | RefreshPolicy::WaitFor => Err(EngineError::InvalidRequest {
                reason: "refresh policy writes are not supported by this engine".to_string(),
            }),
        }
    }
    fn index_document_with_control(
        &self,
        request: ConditionalIndexDocumentRequest,
    ) -> EngineResult<IndexDocumentResponse> {
        if request.condition == WriteCondition::default() {
            self.index_document(request.request)
        } else {
            Err(EngineError::InvalidRequest {
                reason: "conditional index writes are not supported by this engine".to_string(),
            })
        }
    }
    fn replay_document(
        &self,
        request: ReplayDocumentRequest,
    ) -> EngineResult<IndexDocumentResponse>;
    fn update_document(
        &self,
        request: UpdateDocumentRequest,
    ) -> EngineResult<IndexDocumentResponse>;
    fn update_document_with_refresh(
        &self,
        request: UpdateDocumentRequest,
        refresh_policy: RefreshPolicy,
    ) -> EngineResult<IndexDocumentResponse> {
        match refresh_policy {
            RefreshPolicy::None => self.update_document(request),
            RefreshPolicy::Immediate | RefreshPolicy::WaitFor => Err(EngineError::InvalidRequest {
                reason: "refresh policy writes are not supported by this engine".to_string(),
            }),
        }
    }
    fn update_document_with_control(
        &self,
        request: ConditionalUpdateDocumentRequest,
    ) -> EngineResult<IndexDocumentResponse> {
        if request.condition == WriteCondition::default() {
            self.update_document(request.request)
        } else {
            Err(EngineError::InvalidRequest {
                reason: "conditional update writes are not supported by this engine".to_string(),
            })
        }
    }
    fn delete_document(
        &self,
        request: DeleteDocumentRequest,
    ) -> EngineResult<IndexDocumentResponse>;
    fn delete_document_with_refresh(
        &self,
        request: DeleteDocumentRequest,
        refresh_policy: RefreshPolicy,
    ) -> EngineResult<IndexDocumentResponse> {
        match refresh_policy {
            RefreshPolicy::None => self.delete_document(request),
            RefreshPolicy::Immediate | RefreshPolicy::WaitFor => Err(EngineError::InvalidRequest {
                reason: "refresh policy writes are not supported by this engine".to_string(),
            }),
        }
    }
    fn delete_document_with_control(
        &self,
        request: ConditionalDeleteDocumentRequest,
    ) -> EngineResult<IndexDocumentResponse> {
        if request.condition == WriteCondition::default() {
            self.delete_document(request.request)
        } else {
            Err(EngineError::InvalidRequest {
                reason: "conditional delete writes are not supported by this engine".to_string(),
            })
        }
    }
    fn bulk_write(&self, request: BulkWriteRequest) -> EngineResult<BulkWriteResponse> {
        let mut items = Vec::with_capacity(request.operations.len());
        let mut errors = false;
        for operation in request.operations {
            let item = match operation {
                BulkWriteOperation::Index(request) => {
                    let index = request.index.clone();
                    let id = request.id.clone();
                    bulk_item_from_result(
                        WriteOperationKind::Index,
                        index,
                        id,
                        self.index_document(request),
                    )
                }
                BulkWriteOperation::Create(request) => {
                    let index = request.index.clone();
                    let id = request.id.clone();
                    bulk_item_from_result(
                        WriteOperationKind::Create,
                        index,
                        id,
                        self.index_document(request),
                    )
                }
                BulkWriteOperation::Delete(request) => {
                    let index = request.index.clone();
                    let id = request.id.clone();
                    bulk_item_from_result(
                        WriteOperationKind::Delete,
                        index,
                        id,
                        self.delete_document(request),
                    )
                }
                BulkWriteOperation::Update(request) => {
                    let index = request.index.clone();
                    let id = request.id.clone();
                    bulk_item_from_result(
                        WriteOperationKind::Update,
                        index,
                        id,
                        self.update_document(request),
                    )
                }
                BulkWriteOperation::Replay(request) => {
                    let index = request.index.clone();
                    let id = request.metadata.id.clone();
                    bulk_item_from_result(
                        WriteOperationKind::Replay,
                        index,
                        id,
                        self.replay_document(request),
                    )
                }
            };
            errors |= item.error_type.is_some();
            items.push(item);
        }
        Ok(BulkWriteResponse { errors, items })
    }
    fn get_document(
        &self,
        request: GetDocumentRequest,
    ) -> EngineResult<Option<GetDocumentResponse>>;
    fn refresh(&self, request: RefreshRequest) -> EngineResult<RefreshResponse>;
    fn estimate_search_memory_reservation(
        &self,
        request: &SearchRequest,
    ) -> EngineResult<SearchMemoryReservation> {
        let counters = self.search_memory_usage_counters(request)?;
        Ok(SearchMemoryReservation {
            doc_values_bytes: counters.doc_values_bytes,
            vector_bytes: counters
                .vector_bytes
                .saturating_add(counters.collector_bytes)
                .saturating_add(counters.cache_bytes),
            transport_bytes: counters.transport_bytes,
        })
    }
    fn search_memory_usage_counters(
        &self,
        _request: &SearchRequest,
    ) -> EngineResult<SearchMemoryUsageCounters> {
        Ok(SearchMemoryUsageCounters::default())
    }
    fn search_cache_telemetry_snapshot(&self) -> EngineResult<SearchCacheTelemetrySnapshot> {
        Ok(SearchCacheTelemetrySnapshot::default())
    }
    fn search_cache_telemetry_details(&self) -> EngineResult<SearchCacheTelemetryDetails> {
        Ok(SearchCacheTelemetryDetails::default())
    }
    fn search(&self, request: SearchRequest) -> EngineResult<SearchResponse>;
    fn persist_shard_state(&self, index: &str, shard_path: &Path) -> EngineResult<ShardManifest> {
        let _ = (index, shard_path);
        Err(EngineError::InvalidRequest {
            reason: "shard state persistence is not supported by this engine".to_string(),
        })
    }
    fn recover_index_from_manifest(
        &self,
        index: String,
        request: CreateIndexRequest,
        shard_path: &Path,
    ) -> EngineResult<ShardManifest> {
        let _ = (index, request, shard_path);
        Err(EngineError::InvalidRequest {
            reason: "manifest recovery is not supported by this engine".to_string(),
        })
    }
}

fn bulk_item_from_result(
    operation: WriteOperationKind,
    index: String,
    id: String,
    result: EngineResult<IndexDocumentResponse>,
) -> BulkWriteItemResponse {
    match result {
        Ok(response) => {
            let status = match response.result {
                WriteResult::Created => 201,
                WriteResult::Updated | WriteResult::Deleted => 200,
            };
            BulkWriteItemResponse {
                operation,
                index: response.index,
                id: response.metadata.id.clone(),
                status,
                result: Some(response.result),
                metadata: Some(response.metadata),
                coordination: Some(response.coordination),
                error_type: None,
                reason: None,
            }
        }
        Err(error) => BulkWriteItemResponse {
            operation,
            index,
            id,
            status: error.status_code(),
            result: None,
            metadata: None,
            coordination: None,
            error_type: Some(error.opensearch_error_type().to_string()),
            reason: Some(error.opensearch_reason()),
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    #[derive(Default)]
    struct NoopEngine;

    impl IndexEngine for NoopEngine {
        fn create_index(&self, request: CreateIndexRequest) -> EngineResult<CreateIndexResponse> {
            Ok(CreateIndexResponse {
                index: request.index,
                acknowledged: true,
            })
        }

        fn index_document(
            &self,
            request: IndexDocumentRequest,
        ) -> EngineResult<IndexDocumentResponse> {
            Ok(IndexDocumentResponse {
                index: request.index,
                metadata: DocumentMetadata {
                    id: request.id,
                    version: 1,
                    seq_no: 0,
                    primary_term: 1,
                },
                coordination: WriteCoordinationMetadata::default(),
                result: WriteResult::Created,
            })
        }

        fn replay_document(
            &self,
            request: ReplayDocumentRequest,
        ) -> EngineResult<IndexDocumentResponse> {
            Ok(IndexDocumentResponse {
                index: request.index,
                metadata: request.metadata,
                coordination: request.coordination,
                result: WriteResult::Updated,
            })
        }

        fn update_document(
            &self,
            request: UpdateDocumentRequest,
        ) -> EngineResult<IndexDocumentResponse> {
            Ok(IndexDocumentResponse {
                index: request.index,
                metadata: DocumentMetadata {
                    id: request.id,
                    version: 2,
                    seq_no: 1,
                    primary_term: 1,
                },
                coordination: WriteCoordinationMetadata::default(),
                result: WriteResult::Updated,
            })
        }

        fn delete_document(
            &self,
            request: DeleteDocumentRequest,
        ) -> EngineResult<IndexDocumentResponse> {
            Ok(IndexDocumentResponse {
                index: request.index,
                metadata: DocumentMetadata {
                    id: request.id,
                    version: 2,
                    seq_no: 1,
                    primary_term: 1,
                },
                coordination: WriteCoordinationMetadata::default(),
                result: WriteResult::Deleted,
            })
        }

        fn get_document(
            &self,
            request: GetDocumentRequest,
        ) -> EngineResult<Option<GetDocumentResponse>> {
            Ok(Some(GetDocumentResponse {
                index: request.index,
                metadata: DocumentMetadata {
                    id: request.id,
                    version: 1,
                    seq_no: 0,
                    primary_term: 1,
                },
                source: serde_json::json!({ "message": "hello" }),
                found: true,
            }))
        }

        fn refresh(&self, _request: RefreshRequest) -> EngineResult<RefreshResponse> {
            Ok(RefreshResponse { refreshed: true })
        }

        fn search(&self, _request: SearchRequest) -> EngineResult<SearchResponse> {
            Ok(SearchResponse::new(0, Vec::new(), serde_json::json!({})))
        }
    }

    #[test]
    fn trait_contract_covers_mvp_engine_operations() {
        let engine = NoopEngine;

        let create = engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({}),
            })
            .unwrap();
        let index = engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({ "message": "hello" }),
            })
            .unwrap();
        let get = engine
            .get_document(GetDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
            })
            .unwrap()
            .unwrap();
        let refresh = engine
            .refresh(RefreshRequest {
                indices: vec!["logs-000001".to_string()],
            })
            .unwrap();
        let search = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "match_all": {} }),
                aggregations: serde_json::json!({}),
                sort: Vec::new(),
                from: 0,
                size: 10,
            })
            .unwrap();

        assert_eq!(create.index, "logs-000001");
        assert!(create.acknowledged);
        assert_eq!(index.result, WriteResult::Created);
        assert_eq!(index.metadata.id, "1");
        assert_eq!(get.source["message"], "hello");
        assert_eq!(get.metadata.version, 1);
        assert_eq!(get.metadata.seq_no, 0);
        assert_eq!(get.metadata.primary_term, 1);
        assert!(refresh.refreshed);
        assert_eq!(search.total_hits, 0);
    }

    #[test]
    fn trait_contract_covers_delete_write_operation() {
        let engine = NoopEngine;
        let delete = engine
            .delete_document(DeleteDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
            })
            .unwrap();

        assert_eq!(delete.index, "logs-000001");
        assert_eq!(delete.result, WriteResult::Deleted);
        assert_eq!(delete.metadata.id, "1");
        assert_eq!(delete.metadata.seq_no, 1);
    }

    #[test]
    fn trait_contract_covers_bulk_write_operation() {
        let engine = NoopEngine;
        let bulk = engine
            .bulk_write(BulkWriteRequest {
                operations: vec![
                    BulkWriteOperation::Index(IndexDocumentRequest {
                        index: "logs-000001".to_string(),
                        id: "1".to_string(),
                        source: serde_json::json!({ "message": "hello" }),
                    }),
                    BulkWriteOperation::Update(UpdateDocumentRequest {
                        index: "logs-000001".to_string(),
                        id: "1".to_string(),
                        doc: serde_json::json!({ "message": "updated" }),
                        doc_as_upsert: false,
                    }),
                    BulkWriteOperation::Delete(DeleteDocumentRequest {
                        index: "logs-000001".to_string(),
                        id: "1".to_string(),
                    }),
                ],
            })
            .unwrap();

        assert!(!bulk.errors);
        assert_eq!(bulk.items.len(), 3);
        assert_eq!(bulk.items[0].operation, WriteOperationKind::Index);
        assert_eq!(bulk.items[0].status, 201);
        assert_eq!(bulk.items[1].operation, WriteOperationKind::Update);
        assert_eq!(bulk.items[1].result, Some(WriteResult::Updated));
        assert_eq!(bulk.items[2].operation, WriteOperationKind::Delete);
        assert_eq!(bulk.items[2].result, Some(WriteResult::Deleted));
    }

    #[test]
    fn trait_contract_separates_primary_writes_from_replica_replay() {
        let engine = NoopEngine;
        let replay = engine
            .replay_document(ReplayDocumentRequest {
                index: "logs-000001".to_string(),
                metadata: DocumentMetadata {
                    id: "1".to_string(),
                    version: 7,
                    seq_no: 42,
                    primary_term: 3,
                },
                coordination: WriteCoordinationMetadata {
                    translog_location: Some(TranslogLocation {
                        generation: 2,
                        offset: 4096,
                        size: 128,
                    }),
                    global_checkpoint: 41,
                    local_checkpoint: 42,
                    retention_leases: vec![RetentionLease {
                        id: "lease-1".to_string(),
                        retaining_sequence_number: 12,
                        source: "replica".to_string(),
                        timestamp_millis: 1000,
                    }],
                    noop: true,
                },
                source: serde_json::json!({ "message": "replica" }),
            })
            .unwrap();

        assert_eq!(replay.index, "logs-000001");
        assert_eq!(replay.metadata.version, 7);
        assert_eq!(replay.metadata.seq_no, 42);
        assert_eq!(replay.metadata.primary_term, 3);
        assert_eq!(replay.coordination.global_checkpoint, 41);
        assert_eq!(replay.coordination.local_checkpoint, 42);
        assert_eq!(replay.coordination.retention_leases.len(), 1);
        assert!(replay.coordination.noop);
    }

    #[test]
    fn document_metadata_serializes_with_opensearch_field_names() {
        let value = serde_json::to_value(DocumentMetadata {
            id: "1".to_string(),
            version: 3,
            seq_no: 2,
            primary_term: 1,
        })
        .unwrap();

        assert_eq!(value["_id"], "1");
        assert_eq!(value["_version"], 3);
        assert_eq!(value["_seq_no"], 2);
        assert_eq!(value["_primary_term"], 1);
    }

    #[test]
    fn search_response_converts_to_opensearch_hit_shape() {
        let response = SearchResponse::new(
            1,
            vec![SearchHit {
                index: "logs-000001".to_string(),
                metadata: DocumentMetadata {
                    id: "1".to_string(),
                    version: 3,
                    seq_no: 2,
                    primary_term: 1,
                },
                score: 1.0,
                source: serde_json::json!({
                    "message": "hello"
                }),
            }],
            serde_json::json!({
                "by_service": {
                    "buckets": [
                        {
                            "key": "api",
                            "doc_count": 1
                        }
                    ]
                }
            }),
        );

        let body = response.to_opensearch_body(7);

        assert_eq!(body["took"], 7);
        assert_eq!(body["timed_out"], false);
        assert_eq!(body["_shards"]["total"], 1);
        assert_eq!(body["hits"]["total"]["value"], 1);
        assert_eq!(body["hits"]["total"]["relation"], "eq");
        assert_eq!(body["hits"]["max_score"], 1.0);
        assert_eq!(body["hits"]["hits"][0]["_index"], "logs-000001");
        assert_eq!(body["hits"]["hits"][0]["_id"], "1");
        assert_eq!(body["hits"]["hits"][0]["_score"], 1.0);
        assert_eq!(body["hits"]["hits"][0]["_source"]["message"], "hello");
        assert_eq!(body["hits"]["hits"][0]["_version"], 3);
        assert_eq!(body["hits"]["hits"][0]["_seq_no"], 2);
        assert_eq!(body["hits"]["hits"][0]["_primary_term"], 1);
        assert_eq!(
            body["aggregations"]["by_service"]["buckets"][0]["key"],
            "api"
        );
        assert_eq!(
            body["aggregations"]["by_service"]["buckets"][0]["doc_count"],
            1
        );
    }

    #[test]
    fn empty_search_response_uses_null_max_score() {
        let body = SearchResponse::new(0, Vec::new(), serde_json::json!({})).to_opensearch_body(0);

        assert_eq!(body["hits"]["total"]["value"], 0);
        assert_eq!(body["hits"]["max_score"], Value::Null);
        assert!(body["hits"]["hits"].as_array().unwrap().is_empty());
    }

    #[test]
    fn search_response_exposes_shard_failures_and_profile() {
        let shards = SearchShardStats {
            total: 1,
            successful: 0,
            skipped: 0,
            failed: 1,
            failures: vec![SearchShardFailure {
                index: Some("logs-000001".to_string()),
                shard: Some(0),
                node: Some("node-a".to_string()),
                reason: "query failed".to_string(),
                status: 500,
            }],
        };
        let phases = vec![
            SearchPhaseResult::completed(SearchPhase::CanMatch, "target accepted"),
            SearchPhaseResult::skipped(SearchPhase::Dfs, "single shard"),
        ];
        let fetch_subphases = vec![SearchFetchSubphaseResult::completed(
            SearchFetchSubphase::Source,
            "loaded _source",
        )];
        let body = SearchResponse::new(0, Vec::new(), serde_json::json!({}))
            .with_shards(shards)
            .with_phase_results(phases.clone())
            .with_fetch_subphases(fetch_subphases.clone())
            .with_profile(SearchProfile::from_phases(phases).with_fetch_subphases(fetch_subphases))
            .to_opensearch_body(3);

        assert_eq!(body["_shards"]["failed"], 1);
        assert_eq!(body["_shards"]["failures"][0]["index"], "logs-000001");
        assert_eq!(body["_shards"]["failures"][0]["shard"], 0);
        assert_eq!(body["_shards"]["failures"][0]["node"], "node-a");
        assert_eq!(
            body["_shards"]["failures"][0]["reason"]["reason"],
            "query failed"
        );
        assert!(body["profile"]["shards"][0]["searches"][0]["query"].is_array());
        assert_eq!(
            body["profile"]["shards"][0]["searches"][0]["fetch"]["children"][0]["description"],
            "loaded _source"
        );
    }

    #[test]
    fn merge_shard_search_results_collects_hits_and_partial_failures() {
        let left = SearchShardTarget {
            index: "logs-000001".to_string(),
            shard: 0,
            node: "node-a".to_string(),
        };
        let right = SearchShardTarget {
            index: "logs-000001".to_string(),
            shard: 1,
            node: "node-b".to_string(),
        };
        let failed = SearchShardTarget {
            index: "logs-000001".to_string(),
            shard: 2,
            node: "node-c".to_string(),
        };
        let merged = merge_shard_search_results(
            vec![
                SearchShardSearchResult::success(
                    left,
                    SearchResponse::new(
                        1,
                        vec![SearchHit {
                            index: "logs-000001".to_string(),
                            metadata: DocumentMetadata {
                                id: "left".to_string(),
                                version: 1,
                                seq_no: 0,
                                primary_term: 1,
                            },
                            score: 0.4,
                            source: serde_json::json!({ "message": "left" }),
                        }],
                        serde_json::json!({}),
                    )
                    .with_phase_results(vec![SearchPhaseResult::completed(
                        SearchPhase::Query,
                        "left query",
                    )])
                    .with_fetch_subphases(vec![
                        SearchFetchSubphaseResult::completed(
                            SearchFetchSubphase::Source,
                            "left source",
                        ),
                    ]),
                ),
                SearchShardSearchResult::success(
                    right,
                    SearchResponse::new(
                        1,
                        vec![SearchHit {
                            index: "logs-000001".to_string(),
                            metadata: DocumentMetadata {
                                id: "right".to_string(),
                                version: 1,
                                seq_no: 0,
                                primary_term: 1,
                            },
                            score: 0.9,
                            source: serde_json::json!({ "message": "right" }),
                        }],
                        serde_json::json!({}),
                    )
                    .with_phase_results(vec![SearchPhaseResult::completed(
                        SearchPhase::Query,
                        "right query",
                    )])
                    .with_fetch_subphases(vec![
                        SearchFetchSubphaseResult::completed(
                            SearchFetchSubphase::Source,
                            "right source",
                        ),
                    ]),
                ),
                SearchShardSearchResult::failure(failed, "shard unavailable", 503),
            ],
            0,
            10,
        );

        assert_eq!(merged.total_hits, 2);
        assert_eq!(merged.hits[0].metadata.id, "right");
        assert_eq!(merged.hits[1].metadata.id, "left");
        assert_eq!(merged.shards.total, 3);
        assert_eq!(merged.shards.successful, 2);
        assert_eq!(merged.shards.failed, 1);
        assert_eq!(merged.shards.failures[0].reason, "shard unavailable");
        assert_eq!(merged.phase_results.len(), 2);
        assert_eq!(merged.fetch_subphases.len(), 2);
    }

    #[test]
    fn engine_errors_expose_rest_translation_fields() {
        let duplicate = EngineError::IndexAlreadyExists {
            index: "logs-000001".to_string(),
        };
        let missing_index = EngineError::IndexNotFound {
            index: "missing".to_string(),
        };
        let missing_document = EngineError::DocumentNotFound {
            index: "logs-000001".to_string(),
            id: "1".to_string(),
        };

        assert_eq!(duplicate.status_code(), 400);
        assert_eq!(
            duplicate.opensearch_error_type(),
            "resource_already_exists_exception"
        );
        assert_eq!(
            duplicate.opensearch_reason(),
            "index [logs-000001] already exists"
        );
        assert_eq!(missing_index.status_code(), 404);
        assert_eq!(
            missing_index.opensearch_error_type(),
            "index_not_found_exception"
        );
        assert_eq!(missing_document.status_code(), 404);
        assert_eq!(
            missing_document.opensearch_error_type(),
            "document_missing_exception"
        );
    }

    #[test]
    fn persists_and_loads_shard_manifest() {
        let path = unique_temp_path("os-engine-manifest");
        let manifest = ShardManifest {
            index_uuid: "index-uuid".to_string(),
            shard_id: 0,
            allocation_id: "allocation-id".to_string(),
            primary_term: 7,
            max_sequence_number: 42,
            local_checkpoint: 41,
            refreshed_sequence_number: 40,
            committed_generation: 3,
            translog_generation: 5,
            schema_hash: 99,
            vector_segments: Vec::new(),
        };

        persist_shard_manifest(&path, &manifest).unwrap();
        let loaded = load_shard_manifest(&path).unwrap();

        assert_eq!(loaded, manifest);
        let _ = fs::remove_dir_all(path);
    }

    #[test]
    fn load_shard_manifest_rejects_checksum_mismatch() {
        let path = unique_temp_path("os-engine-manifest-checksum");
        let manifest = ShardManifest {
            index_uuid: "index-uuid".to_string(),
            shard_id: 0,
            allocation_id: "allocation-id".to_string(),
            primary_term: 7,
            max_sequence_number: 42,
            local_checkpoint: 41,
            refreshed_sequence_number: 40,
            committed_generation: 3,
            translog_generation: 5,
            schema_hash: 99,
            vector_segments: Vec::new(),
        };
        persist_shard_manifest(&path, &manifest).unwrap();
        let manifest_path = ShardManifest::manifest_path(&path);
        let tampered = fs::read_to_string(&manifest_path)
            .unwrap()
            .replace("\"primary_term\": 7", "\"primary_term\": 8");
        fs::write(&manifest_path, tampered).unwrap();

        let error = load_shard_manifest(&path).unwrap_err();

        assert_eq!(error.status_code(), 500);
        assert!(error.opensearch_reason().contains("checksum mismatch"));
        let _ = fs::remove_dir_all(path);
    }

    fn unique_temp_path(name: &str) -> PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock should be after unix epoch")
            .as_nanos();
        std::env::temp_dir().join(format!("{name}-{}-{nanos}", std::process::id()))
    }
}
