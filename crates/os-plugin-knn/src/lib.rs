//! Static k-NN plugin surface for Steelsearch.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

pub const KNN_PLUGIN_NAME: &str = "opensearch-knn";
pub const KNN_VECTOR_FIELD_TYPE: &str = "knn_vector";
pub const KNN_QUERY_CLAUSE: &str = "knn";
pub const KNN_VECTOR_FORMAT: &str = "steelsearch-knn-vector";
pub const KNN_SCORE_SCRIPT_CONTEXT: &str = "knn_score";
pub const KNN_SEARCH_PIPELINE_PROCESSOR: &str = "knn";
pub const KNN_STATS_ACTION: &str = "cluster:admin/knn/stats";
pub const KNN_WARMUP_ACTION: &str = "cluster:admin/knn/warmup";
pub const KNN_CLEAR_CACHE_ACTION: &str = "cluster:admin/knn/clear_cache";
pub const KNN_MODEL_GET_ACTION: &str = "cluster:admin/knn/model/get";
pub const KNN_MODEL_DELETE_ACTION: &str = "cluster:admin/knn/model/delete";
pub const KNN_MODEL_SEARCH_ACTION: &str = "cluster:admin/knn/model/search";
pub const KNN_MODEL_TRAIN_ACTION: &str = "cluster:admin/knn/model/train";
pub const KNN_MEMORY_CIRCUIT_BREAKER: &str = "knn.memory";
pub const KNN_REMOTE_INDEX_BUILD_HOOK: &str = "knn.remote_index_build";

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnVectorMapping {
    pub dimension: usize,
    pub data_type: KnnVectorDataType,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub model_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub method: Option<KnnMethodDefinition>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub mode: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub compression_level: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub engine: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub space_type: Option<String>,
    pub doc_values: bool,
    pub stored: bool,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub metadata: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum KnnVectorDataType {
    Float,
    Byte,
    Binary,
}

impl Default for KnnVectorDataType {
    fn default() -> Self {
        Self::Float
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnMethodDefinition {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub engine: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub space_type: Option<String>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub parameters: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct KnnMappingError {
    reason: String,
}

impl KnnMappingError {
    fn new(reason: impl Into<String>) -> Self {
        Self {
            reason: reason.into(),
        }
    }
}

impl fmt::Display for KnnMappingError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.reason)
    }
}

impl std::error::Error for KnnMappingError {}

pub fn parse_knn_vector_mapping(value: &Value) -> Result<KnnVectorMapping, KnnMappingError> {
    let Some(object) = value.as_object() else {
        return Err(KnnMappingError::new("knn_vector mapping must be an object"));
    };

    for option in object.keys() {
        if !matches!(
            option.as_str(),
            "type"
                | "dimension"
                | "data_type"
                | "model_id"
                | "method"
                | "mode"
                | "compression_level"
                | "engine"
                | "space_type"
                | "doc_values"
                | "store"
                | "metadata"
                | "index"
        ) {
            return Err(KnnMappingError::new(format!(
                "unsupported knn_vector mapping option [{option}]"
            )));
        }
    }

    if let Some(field_type) = object.get("type").and_then(Value::as_str) {
        if field_type != KNN_VECTOR_FIELD_TYPE {
            return Err(KnnMappingError::new(format!(
                "knn_vector mapping type must be [{KNN_VECTOR_FIELD_TYPE}]"
            )));
        }
    }

    let Some(dimension) = object.get("dimension") else {
        return Err(KnnMappingError::new(
            "knn_vector mapping requires [dimension]",
        ));
    };
    let dimension = dimension
        .as_u64()
        .filter(|dimension| *dimension > 0)
        .and_then(|dimension| usize::try_from(dimension).ok())
        .ok_or_else(|| KnnMappingError::new("knn_vector [dimension] must be a positive integer"))?;

    let data_type = match object
        .get("data_type")
        .and_then(Value::as_str)
        .unwrap_or("float")
    {
        "float" => KnnVectorDataType::Float,
        "byte" => KnnVectorDataType::Byte,
        "binary" => KnnVectorDataType::Binary,
        other => {
            return Err(KnnMappingError::new(format!(
                "unsupported knn_vector data_type [{other}]"
            )))
        }
    };

    Ok(KnnVectorMapping {
        dimension,
        data_type,
        model_id: optional_string(object.get("model_id"), "model_id")?,
        method: optional_method(object.get("method"))?,
        mode: optional_string(object.get("mode"), "mode")?,
        compression_level: optional_string(object.get("compression_level"), "compression_level")?,
        engine: optional_string(object.get("engine"), "engine")?,
        space_type: optional_string(object.get("space_type"), "space_type")?,
        doc_values: optional_bool(object.get("doc_values"), "doc_values")?.unwrap_or(true),
        stored: optional_bool(object.get("store"), "store")?.unwrap_or(false),
        metadata: optional_value_object(object.get("metadata"), "metadata")?,
    })
}

fn optional_string(value: Option<&Value>, name: &str) -> Result<Option<String>, KnnMappingError> {
    value
        .map(|value| {
            value.as_str().map(ToString::to_string).ok_or_else(|| {
                KnnMappingError::new(format!("knn_vector [{name}] must be a string"))
            })
        })
        .transpose()
}

fn optional_bool(value: Option<&Value>, name: &str) -> Result<Option<bool>, KnnMappingError> {
    value
        .map(|value| {
            value.as_bool().ok_or_else(|| {
                KnnMappingError::new(format!("knn_vector [{name}] must be a boolean"))
            })
        })
        .transpose()
}

fn optional_value_object(
    value: Option<&Value>,
    name: &str,
) -> Result<BTreeMap<String, Value>, KnnMappingError> {
    let Some(value) = value else {
        return Ok(BTreeMap::new());
    };
    let Some(object) = value.as_object() else {
        return Err(KnnMappingError::new(format!(
            "knn_vector [{name}] must be an object"
        )));
    };
    Ok(object
        .iter()
        .map(|(key, value)| (key.clone(), value.clone()))
        .collect())
}

fn optional_method(value: Option<&Value>) -> Result<Option<KnnMethodDefinition>, KnnMappingError> {
    let Some(value) = value else {
        return Ok(None);
    };
    let Some(object) = value.as_object() else {
        return Err(KnnMappingError::new(
            "knn_vector [method] must be an object",
        ));
    };
    for option in object.keys() {
        if !matches!(
            option.as_str(),
            "name" | "engine" | "space_type" | "parameters"
        ) {
            return Err(KnnMappingError::new(format!(
                "unsupported knn_vector method option [{option}]"
            )));
        }
    }
    Ok(Some(KnnMethodDefinition {
        name: optional_string(object.get("name"), "method.name")?,
        engine: optional_string(object.get("engine"), "method.engine")?,
        space_type: optional_string(object.get("space_type"), "method.space_type")?,
        parameters: optional_value_object(object.get("parameters"), "method.parameters")?,
    }))
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnPlugin {
    pub name: String,
    pub extensions: KnnExtensionPoints,
    #[serde(default)]
    pub state: KnnPluginState,
}

impl Default for KnnPlugin {
    fn default() -> Self {
        Self {
            name: KNN_PLUGIN_NAME.to_string(),
            extensions: KnnExtensionPoints::default(),
            state: KnnPluginState::default(),
        }
    }
}

impl KnnPlugin {
    pub fn extension_points(&self) -> &KnnExtensionPoints {
        &self.extensions
    }

    pub fn plugin_info(&self) -> serde_json::Value {
        serde_json::json!({
            "name": self.name,
            "mapper": self.extensions.mapper_field_types,
            "query": self.extensions.query_clauses,
            "rest_actions": self.extensions.rest_actions,
            "codec_vector_formats": self.extensions.codec_vector_formats,
            "script_contexts": self.extensions.script_contexts,
            "search_pipeline_processors": self.extensions.search_pipeline_processors,
            "stats_actions": self.extensions.stats_actions,
            "circuit_breakers": self.extensions.circuit_breakers
        })
    }

    pub fn stats(&self) -> KnnStats {
        let mut stats = self.state.stats.clone();
        stats.model_count = self.state.models.len();
        stats.trained_model_count = self
            .state
            .models
            .values()
            .filter(|model| model.state == KnnModelState::Trained)
            .count();
        stats.warmed_index_count = self.state.warmed_indices.len();
        stats.cache_entry_count = self.state.cache_entries.len();
        stats.native_memory_used_bytes = self.state.native_memory.used_bytes;
        stats.native_memory_peak_bytes = self.state.native_memory.peak_bytes;
        stats.model_cache_used_bytes = self.state.model_cache.used_bytes;
        stats.quantization_cache_used_bytes = self.state.quantization_cache.used_bytes;
        stats
    }

    pub fn warmup(
        &mut self,
        request: KnnWarmupRequest,
    ) -> Result<KnnWarmupResponse, KnnPluginApiError> {
        self.state.stats.warmup_requests += 1;
        let graph_cache_key = format!("{}:graphs", request.index);
        self.reserve_native_memory_entry(graph_cache_key.clone(), request.native_memory_bytes)?;
        if request.model_cache_bytes > 0 {
            self.record_model_cache_entry(
                format!("{}:model", request.index),
                request.model_cache_bytes,
            );
        }
        if request.quantization_cache_bytes > 0 {
            self.record_quantization_cache_entry(
                format!("{}:quantization", request.index),
                request.quantization_cache_bytes,
            );
        }
        let warmed = self.state.warmed_indices.insert(request.index.clone());
        self.state.stats.graph_count += request.vector_segment_count;
        self.state.cache_entries.insert(graph_cache_key);
        Ok(KnnWarmupResponse {
            index: request.index,
            warmed,
            vector_segment_count: request.vector_segment_count,
            native_memory_bytes: request.native_memory_bytes,
            model_cache_bytes: request.model_cache_bytes,
            quantization_cache_bytes: request.quantization_cache_bytes,
        })
    }

    pub fn clear_cache(&mut self, request: KnnClearCacheRequest) -> KnnClearCacheResponse {
        let prefix = format!("{}:", request.index);
        let before = self.state.cache_entries.len();
        self.state
            .cache_entries
            .retain(|entry| !entry.starts_with(&prefix));
        let cleared_entries = before - self.state.cache_entries.len();
        let (cleared_native_entries, released_native_memory_bytes) =
            clear_native_memory_prefix(&mut self.state.native_memory, &prefix);
        let (cleared_model_entries, released_model_cache_bytes) =
            clear_cache_prefix(&mut self.state.model_cache, &prefix);
        let (cleared_quantization_entries, released_quantization_cache_bytes) =
            clear_cache_prefix(&mut self.state.quantization_cache, &prefix);
        self.state.warmed_indices.remove(&request.index);
        self.state.stats.clear_cache_requests += 1;
        self.state.stats.cache_evictions += cleared_entries
            + cleared_native_entries
            + cleared_model_entries
            + cleared_quantization_entries;
        KnnClearCacheResponse {
            index: request.index,
            cleared_entries,
            released_native_memory_bytes,
            released_model_cache_bytes,
            released_quantization_cache_bytes,
        }
    }

    pub fn train_model(
        &mut self,
        request: KnnModelTrainingRequest,
    ) -> Result<KnnModelDefinition, KnnPluginApiError> {
        if self.state.models.contains_key(&request.model_id) {
            return Err(KnnPluginApiError::ModelAlreadyExists {
                model_id: request.model_id,
            });
        }
        let model = KnnModelDefinition {
            model_id: request.model_id.clone(),
            state: KnnModelState::Trained,
            dimension: request.dimension,
            method: request.method,
            training_index: request.training_index,
            training_field: request.training_field,
            metadata: request.metadata,
        };
        self.state
            .cache_entries
            .insert(format!("model:{}", model.model_id));
        self.state
            .models
            .insert(model.model_id.clone(), model.clone());
        self.state.stats.model_training_requests += 1;
        Ok(model)
    }

    pub fn get_model(&self, model_id: &str) -> Result<KnnModelDefinition, KnnPluginApiError> {
        self.state
            .models
            .get(model_id)
            .cloned()
            .ok_or_else(|| KnnPluginApiError::ModelNotFound {
                model_id: model_id.to_string(),
            })
    }

    pub fn delete_model(
        &mut self,
        model_id: &str,
    ) -> Result<KnnModelDefinition, KnnPluginApiError> {
        let model =
            self.state
                .models
                .remove(model_id)
                .ok_or_else(|| KnnPluginApiError::ModelNotFound {
                    model_id: model_id.to_string(),
                })?;
        self.state
            .cache_entries
            .remove(&format!("model:{model_id}"));
        self.state.stats.model_delete_requests += 1;
        Ok(model)
    }

    pub fn search_models(&self, request: KnnModelSearchRequest) -> KnnModelSearchResponse {
        let mut models =
            self.state
                .models
                .values()
                .filter(|model| {
                    request
                        .state
                        .as_ref()
                        .map_or(true, |state| state == &model.state)
                })
                .filter(|model| {
                    request.query.as_ref().map_or(true, |query| {
                        model.model_id.contains(query)
                            || model.metadata.values().any(|value| {
                                value.as_str().is_some_and(|text| text.contains(query))
                            })
                    })
                })
                .cloned()
                .collect::<Vec<_>>();
        models.sort_by(|left, right| left.model_id.cmp(&right.model_id));
        let total = models.len();
        models.truncate(request.size);
        KnnModelSearchResponse { total, models }
    }

    pub fn operational_controls(&self) -> KnnOperationalControls {
        KnnOperationalControls {
            config: self.state.operational_config.clone(),
            feature_gates: KnnFeatureGates::compiled(),
            native_memory: self.state.native_memory.clone(),
            model_cache: self.state.model_cache.clone(),
            quantization_cache: self.state.quantization_cache.clone(),
            remote_index_builds: self.state.remote_index_builds.clone(),
        }
    }

    pub fn configure_operational_controls(&mut self, config: KnnOperationalConfig) {
        self.state.operational_config = config;
        self.enforce_cache_limits();
    }

    pub fn reserve_native_memory(&mut self, bytes: usize) -> Result<(), KnnPluginApiError> {
        let next = self.state.native_memory.used_bytes.saturating_add(bytes);
        if next > self.state.operational_config.native_memory_limit_bytes {
            self.state.stats.circuit_breaker_triggered = true;
            return Err(KnnPluginApiError::NativeMemoryLimitExceeded {
                requested_bytes: bytes,
                limit_bytes: self.state.operational_config.native_memory_limit_bytes,
            });
        }
        self.state.native_memory.used_bytes = next;
        self.state.native_memory.peak_bytes = self.state.native_memory.peak_bytes.max(next);
        Ok(())
    }

    fn reserve_native_memory_entry(
        &mut self,
        key: String,
        bytes: usize,
    ) -> Result<(), KnnPluginApiError> {
        if bytes == 0 {
            return Ok(());
        }
        let previous_bytes = self
            .state
            .native_memory
            .entries
            .get(&key)
            .copied()
            .unwrap_or(0);
        let next = self
            .state
            .native_memory
            .used_bytes
            .saturating_sub(previous_bytes)
            .saturating_add(bytes);
        if next > self.state.operational_config.native_memory_limit_bytes {
            self.state.stats.circuit_breaker_triggered = true;
            return Err(KnnPluginApiError::NativeMemoryLimitExceeded {
                requested_bytes: bytes,
                limit_bytes: self.state.operational_config.native_memory_limit_bytes,
            });
        }
        self.state.native_memory.used_bytes = next;
        self.state.native_memory.peak_bytes = self.state.native_memory.peak_bytes.max(next);
        self.state.native_memory.entries.insert(key, bytes);
        Ok(())
    }

    pub fn release_native_memory(&mut self, bytes: usize) {
        self.state.native_memory.used_bytes =
            self.state.native_memory.used_bytes.saturating_sub(bytes);
    }

    pub fn record_model_cache_entry(&mut self, model_id: impl Into<String>, bytes: usize) {
        record_cache_entry(
            &mut self.state.model_cache,
            model_id.into(),
            bytes,
            self.state.operational_config.model_cache_limit_bytes,
        );
    }

    pub fn record_quantization_cache_entry(&mut self, key: impl Into<String>, bytes: usize) {
        record_cache_entry(
            &mut self.state.quantization_cache,
            key.into(),
            bytes,
            self.state.operational_config.quantization_cache_limit_bytes,
        );
    }

    pub fn plan_remote_index_build(
        &mut self,
        request: KnnRemoteIndexBuildRequest,
    ) -> Result<KnnRemoteIndexBuildPlan, KnnPluginApiError> {
        if !self.state.operational_config.remote_index_build_enabled {
            return Err(KnnPluginApiError::RemoteIndexBuildDisabled);
        }
        if !KnnFeatureGates::compiled().remote_index_build {
            return Err(KnnPluginApiError::FeatureDisabled {
                feature: "remote-index-build".to_string(),
            });
        }
        let plan = KnnRemoteIndexBuildPlan {
            index: request.index,
            field: request.field,
            source_node: request.source_node,
            target_node: request.target_node,
            vector_count: request.vector_count,
            state: KnnRemoteIndexBuildState::Planned,
        };
        self.state.remote_index_builds.push(plan.clone());
        Ok(plan)
    }

    pub fn rolling_restart_check(
        &self,
        request: KnnRollingRestartCheckRequest,
    ) -> KnnRollingRestartCheckResponse {
        let feature_gates = KnnFeatureGates::compiled();
        let compatible = request.previous_feature_gates == feature_gates
            && request.previous_config.remote_index_build_enabled
                == self.state.operational_config.remote_index_build_enabled
            && request.previous_config.native_memory_limit_bytes
                <= self.state.operational_config.native_memory_limit_bytes;
        let reason = (!compatible).then_some(
            "k-NN operational feature gates or memory limits changed across rolling restart"
                .to_string(),
        );
        KnnRollingRestartCheckResponse {
            compatible,
            current_feature_gates: feature_gates,
            reason,
        }
    }

    pub fn compatibility_policy(&self) -> &KnnCompatibilityPolicy {
        &self.state.compatibility_policy
    }

    pub fn configure_compatibility_policy(&mut self, policy: KnnCompatibilityPolicy) {
        self.state.compatibility_policy = policy;
    }

    pub fn validate_hot_path_compatibility(
        &self,
        request: KnnHotPathCompatibilityRequest,
    ) -> Result<KnnHotPathCompatibilityDecision, KnnPluginApiError> {
        if request.lucene_jvm_bridge
            || request.dual_write
            || request.recovery_time_conversion
            || request.java_data_node_store_compatibility
        {
            return Err(KnnPluginApiError::HotPathCompatibilityOutOfScope {
                reason: "Lucene/JVM bridge, dual-write, recovery-time conversion, and Java data-node store compatibility are not allowed in the k-NN hot path".to_string(),
            });
        }
        Ok(KnnHotPathCompatibilityDecision {
            mode: self.state.compatibility_policy.hot_path_mode.clone(),
            offline_import_export_allowed: self
                .state
                .compatibility_policy
                .offline_import_export_allowed,
            later_data_node_compatibility_allowed: self
                .state
                .compatibility_policy
                .later_data_node_compatibility_allowed,
        })
    }

    fn enforce_cache_limits(&mut self) {
        enforce_cache_limit(
            &mut self.state.model_cache,
            self.state.operational_config.model_cache_limit_bytes,
        );
        enforce_cache_limit(
            &mut self.state.quantization_cache,
            self.state.operational_config.quantization_cache_limit_bytes,
        );
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnPluginState {
    pub models: BTreeMap<String, KnnModelDefinition>,
    pub warmed_indices: BTreeSet<String>,
    pub cache_entries: BTreeSet<String>,
    pub stats: KnnStats,
    #[serde(default)]
    pub operational_config: KnnOperationalConfig,
    #[serde(default)]
    pub native_memory: KnnNativeMemoryState,
    #[serde(default)]
    pub model_cache: KnnCacheState,
    #[serde(default)]
    pub quantization_cache: KnnCacheState,
    #[serde(default)]
    pub remote_index_builds: Vec<KnnRemoteIndexBuildPlan>,
    #[serde(default)]
    pub compatibility_policy: KnnCompatibilityPolicy,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnStats {
    pub graph_count: usize,
    pub warmed_index_count: usize,
    pub cache_entry_count: usize,
    pub native_memory_used_bytes: usize,
    pub native_memory_peak_bytes: usize,
    pub model_cache_used_bytes: usize,
    pub quantization_cache_used_bytes: usize,
    pub model_count: usize,
    pub trained_model_count: usize,
    pub warmup_requests: usize,
    pub clear_cache_requests: usize,
    pub model_training_requests: usize,
    pub model_delete_requests: usize,
    pub cache_evictions: usize,
    pub circuit_breaker_triggered: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnOperationalConfig {
    pub native_memory_limit_bytes: usize,
    pub model_cache_limit_bytes: usize,
    pub quantization_cache_limit_bytes: usize,
    pub simd_enabled: bool,
    pub native_library_enabled: bool,
    pub remote_index_build_enabled: bool,
    pub rolling_restart_checks_enabled: bool,
}

impl Default for KnnOperationalConfig {
    fn default() -> Self {
        Self {
            native_memory_limit_bytes: 512 * 1024 * 1024,
            model_cache_limit_bytes: 256 * 1024 * 1024,
            quantization_cache_limit_bytes: 128 * 1024 * 1024,
            simd_enabled: cfg!(feature = "simd"),
            native_library_enabled: cfg!(feature = "native-library"),
            remote_index_build_enabled: cfg!(feature = "remote-index-build"),
            rolling_restart_checks_enabled: true,
        }
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnNativeMemoryState {
    pub used_bytes: usize,
    pub peak_bytes: usize,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub entries: BTreeMap<String, usize>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnCacheState {
    pub used_bytes: usize,
    pub entries: BTreeMap<String, usize>,
    pub evictions: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnFeatureGates {
    pub simd: bool,
    pub native_library: bool,
    pub remote_index_build: bool,
}

impl KnnFeatureGates {
    pub fn compiled() -> Self {
        Self {
            simd: cfg!(feature = "simd"),
            native_library: cfg!(feature = "native-library"),
            remote_index_build: cfg!(feature = "remote-index-build"),
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnOperationalControls {
    pub config: KnnOperationalConfig,
    pub feature_gates: KnnFeatureGates,
    pub native_memory: KnnNativeMemoryState,
    pub model_cache: KnnCacheState,
    pub quantization_cache: KnnCacheState,
    pub remote_index_builds: Vec<KnnRemoteIndexBuildPlan>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnRemoteIndexBuildRequest {
    pub index: String,
    pub field: String,
    pub source_node: String,
    pub target_node: String,
    pub vector_count: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnRemoteIndexBuildPlan {
    pub index: String,
    pub field: String,
    pub source_node: String,
    pub target_node: String,
    pub vector_count: usize,
    pub state: KnnRemoteIndexBuildState,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum KnnRemoteIndexBuildState {
    Planned,
    Running,
    Completed,
    Failed,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnRollingRestartCheckRequest {
    pub previous_feature_gates: KnnFeatureGates,
    pub previous_config: KnnOperationalConfig,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnRollingRestartCheckResponse {
    pub compatible: bool,
    pub current_feature_gates: KnnFeatureGates,
    pub reason: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnCompatibilityPolicy {
    pub hot_path_mode: KnnHotPathMode,
    pub offline_import_export_allowed: bool,
    pub later_data_node_compatibility_allowed: bool,
}

impl Default for KnnCompatibilityPolicy {
    fn default() -> Self {
        Self {
            hot_path_mode: KnnHotPathMode::RustNativeOnly,
            offline_import_export_allowed: true,
            later_data_node_compatibility_allowed: true,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum KnnHotPathMode {
    RustNativeOnly,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnHotPathCompatibilityRequest {
    pub lucene_jvm_bridge: bool,
    pub dual_write: bool,
    pub recovery_time_conversion: bool,
    pub java_data_node_store_compatibility: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnHotPathCompatibilityDecision {
    pub mode: KnnHotPathMode,
    pub offline_import_export_allowed: bool,
    pub later_data_node_compatibility_allowed: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnWarmupRequest {
    pub index: String,
    pub vector_segment_count: usize,
    #[serde(default)]
    pub native_memory_bytes: usize,
    #[serde(default)]
    pub model_cache_bytes: usize,
    #[serde(default)]
    pub quantization_cache_bytes: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnWarmupResponse {
    pub index: String,
    pub warmed: bool,
    pub vector_segment_count: usize,
    pub native_memory_bytes: usize,
    pub model_cache_bytes: usize,
    pub quantization_cache_bytes: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnClearCacheRequest {
    pub index: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnClearCacheResponse {
    pub index: String,
    pub cleared_entries: usize,
    pub released_native_memory_bytes: usize,
    pub released_model_cache_bytes: usize,
    pub released_quantization_cache_bytes: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum KnnModelState {
    Training,
    Trained,
    Failed,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnModelDefinition {
    pub model_id: String,
    pub state: KnnModelState,
    pub dimension: usize,
    pub method: KnnMethodDefinition,
    pub training_index: String,
    pub training_field: String,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub metadata: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnModelTrainingRequest {
    pub model_id: String,
    pub dimension: usize,
    pub method: KnnMethodDefinition,
    pub training_index: String,
    pub training_field: String,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub metadata: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnModelSearchRequest {
    pub query: Option<String>,
    pub state: Option<KnnModelState>,
    pub size: usize,
}

impl Default for KnnModelSearchRequest {
    fn default() -> Self {
        Self {
            query: None,
            state: None,
            size: 10,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnModelSearchResponse {
    pub total: usize,
    pub models: Vec<KnnModelDefinition>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum KnnPluginApiError {
    ModelAlreadyExists {
        model_id: String,
    },
    ModelNotFound {
        model_id: String,
    },
    NativeMemoryLimitExceeded {
        requested_bytes: usize,
        limit_bytes: usize,
    },
    FeatureDisabled {
        feature: String,
    },
    RemoteIndexBuildDisabled,
    HotPathCompatibilityOutOfScope {
        reason: String,
    },
}

impl fmt::Display for KnnPluginApiError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::ModelAlreadyExists { model_id } => {
                write!(formatter, "k-NN model [{model_id}] already exists")
            }
            Self::ModelNotFound { model_id } => {
                write!(formatter, "k-NN model [{model_id}] missing")
            }
            Self::NativeMemoryLimitExceeded {
                requested_bytes,
                limit_bytes,
            } => write!(
                formatter,
                "k-NN native memory request [{requested_bytes}] exceeds limit [{limit_bytes}]"
            ),
            Self::FeatureDisabled { feature } => {
                write!(formatter, "k-NN feature [{feature}] is not enabled")
            }
            Self::RemoteIndexBuildDisabled => {
                formatter.write_str("k-NN remote index build is disabled")
            }
            Self::HotPathCompatibilityOutOfScope { reason } => formatter.write_str(reason),
        }
    }
}

impl std::error::Error for KnnPluginApiError {}

fn record_cache_entry(cache: &mut KnnCacheState, key: String, bytes: usize, limit_bytes: usize) {
    if let Some(previous_bytes) = cache.entries.insert(key, bytes) {
        cache.used_bytes = cache.used_bytes.saturating_sub(previous_bytes);
    }
    cache.used_bytes = cache.used_bytes.saturating_add(bytes);
    enforce_cache_limit(cache, limit_bytes);
}

fn enforce_cache_limit(cache: &mut KnnCacheState, limit_bytes: usize) {
    while cache.used_bytes > limit_bytes {
        let Some((key, bytes)) = cache
            .entries
            .iter()
            .next()
            .map(|(key, bytes)| (key.clone(), *bytes))
        else {
            cache.used_bytes = 0;
            break;
        };
        cache.entries.remove(&key);
        cache.used_bytes = cache.used_bytes.saturating_sub(bytes);
        cache.evictions += 1;
    }
}

fn clear_cache_prefix(cache: &mut KnnCacheState, prefix: &str) -> (usize, usize) {
    let keys = cache
        .entries
        .keys()
        .filter(|key| key.starts_with(prefix))
        .cloned()
        .collect::<Vec<_>>();
    let mut released_bytes = 0usize;
    for key in &keys {
        if let Some(bytes) = cache.entries.remove(key) {
            released_bytes = released_bytes.saturating_add(bytes);
        }
    }
    cache.used_bytes = cache.used_bytes.saturating_sub(released_bytes);
    cache.evictions = cache.evictions.saturating_add(keys.len());
    (keys.len(), released_bytes)
}

fn clear_native_memory_prefix(memory: &mut KnnNativeMemoryState, prefix: &str) -> (usize, usize) {
    let keys = memory
        .entries
        .keys()
        .filter(|key| key.starts_with(prefix))
        .cloned()
        .collect::<Vec<_>>();
    let mut released_bytes = 0usize;
    for key in &keys {
        if let Some(bytes) = memory.entries.remove(key) {
            released_bytes = released_bytes.saturating_add(bytes);
        }
    }
    memory.used_bytes = memory.used_bytes.saturating_sub(released_bytes);
    (keys.len(), released_bytes)
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnExtensionPoints {
    pub mapper_field_types: Vec<String>,
    pub query_clauses: Vec<String>,
    pub rest_actions: Vec<String>,
    pub codec_vector_formats: Vec<String>,
    pub script_contexts: Vec<String>,
    pub search_pipeline_processors: Vec<String>,
    pub stats_actions: Vec<String>,
    pub circuit_breakers: Vec<String>,
}

impl Default for KnnExtensionPoints {
    fn default() -> Self {
        Self {
            mapper_field_types: vec![KNN_VECTOR_FIELD_TYPE.to_string()],
            query_clauses: vec![KNN_QUERY_CLAUSE.to_string()],
            rest_actions: vec![
                "/_plugins/_knn/stats".to_string(),
                "/_plugins/_knn/warmup/{index}".to_string(),
                "/_plugins/_knn/clear_cache/{index}".to_string(),
                "/_plugins/_knn/models/{model_id}".to_string(),
                "/_plugins/_knn/models/_search".to_string(),
                "/_plugins/_knn/models/_train".to_string(),
            ],
            codec_vector_formats: vec![KNN_VECTOR_FORMAT.to_string()],
            script_contexts: vec![KNN_SCORE_SCRIPT_CONTEXT.to_string()],
            search_pipeline_processors: vec![KNN_SEARCH_PIPELINE_PROCESSOR.to_string()],
            stats_actions: vec![
                KNN_STATS_ACTION.to_string(),
                KNN_WARMUP_ACTION.to_string(),
                KNN_CLEAR_CACHE_ACTION.to_string(),
                KNN_MODEL_GET_ACTION.to_string(),
                KNN_MODEL_DELETE_ACTION.to_string(),
                KNN_MODEL_SEARCH_ACTION.to_string(),
                KNN_MODEL_TRAIN_ACTION.to_string(),
            ],
            circuit_breakers: vec![KNN_MEMORY_CIRCUIT_BREAKER.to_string()],
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_plugin_registers_knn_extension_points() {
        let plugin = KnnPlugin::default();
        let extensions = plugin.extension_points();

        assert_eq!(plugin.name, KNN_PLUGIN_NAME);
        assert_eq!(extensions.mapper_field_types, vec![KNN_VECTOR_FIELD_TYPE]);
        assert_eq!(extensions.query_clauses, vec![KNN_QUERY_CLAUSE]);
        assert!(extensions
            .rest_actions
            .iter()
            .any(|route| route == "/_plugins/_knn/stats"));
        assert_eq!(extensions.codec_vector_formats, vec![KNN_VECTOR_FORMAT]);
        assert_eq!(extensions.script_contexts, vec![KNN_SCORE_SCRIPT_CONTEXT]);
        assert_eq!(
            extensions.search_pipeline_processors,
            vec![KNN_SEARCH_PIPELINE_PROCESSOR]
        );
        assert!(extensions
            .stats_actions
            .iter()
            .any(|action| action == KNN_STATS_ACTION));
        assert_eq!(
            extensions.circuit_breakers,
            vec![KNN_MEMORY_CIRCUIT_BREAKER]
        );
    }

    #[test]
    fn plugin_info_exposes_registered_surfaces() {
        let info = KnnPlugin::default().plugin_info();

        assert_eq!(info["name"], KNN_PLUGIN_NAME);
        assert_eq!(info["mapper"], serde_json::json!([KNN_VECTOR_FIELD_TYPE]));
        assert_eq!(info["query"], serde_json::json!([KNN_QUERY_CLAUSE]));
        assert_eq!(
            info["circuit_breakers"],
            serde_json::json!([KNN_MEMORY_CIRCUIT_BREAKER])
        );
    }

    #[test]
    fn parses_full_knn_vector_mapping() {
        let mapping = parse_knn_vector_mapping(&serde_json::json!({
            "type": "knn_vector",
            "dimension": 384,
            "data_type": "float",
            "model_id": "mini-lm",
            "method": {
                "name": "hnsw",
                "engine": "faiss",
                "space_type": "l2",
                "parameters": {
                    "ef_construction": 128,
                    "m": 16
                }
            },
            "mode": "on_disk",
            "compression_level": "16x",
            "engine": "lucene",
            "space_type": "cosinesimil",
            "doc_values": false,
            "store": true,
            "metadata": {
                "source": "minilm"
            }
        }))
        .unwrap();

        assert_eq!(mapping.dimension, 384);
        assert_eq!(mapping.data_type, KnnVectorDataType::Float);
        assert_eq!(mapping.model_id.as_deref(), Some("mini-lm"));
        assert_eq!(
            mapping.method.as_ref().unwrap().name.as_deref(),
            Some("hnsw")
        );
        assert_eq!(
            mapping.method.as_ref().unwrap().parameters["m"],
            serde_json::json!(16)
        );
        assert_eq!(mapping.mode.as_deref(), Some("on_disk"));
        assert_eq!(mapping.compression_level.as_deref(), Some("16x"));
        assert_eq!(mapping.engine.as_deref(), Some("lucene"));
        assert_eq!(mapping.space_type.as_deref(), Some("cosinesimil"));
        assert!(!mapping.doc_values);
        assert!(mapping.stored);
        assert_eq!(mapping.metadata["source"], serde_json::json!("minilm"));
    }

    #[test]
    fn rejects_unsupported_knn_vector_mapping_option() {
        let error = parse_knn_vector_mapping(&serde_json::json!({
            "type": "knn_vector",
            "dimension": 4,
            "unknown": true
        }))
        .unwrap_err();

        assert_eq!(
            error.to_string(),
            "unsupported knn_vector mapping option [unknown]"
        );
    }

    #[test]
    fn plugin_apis_track_stats_warmup_and_cache_clear() {
        let mut plugin = KnnPlugin::default();

        let warmup = plugin
            .warmup(KnnWarmupRequest {
                index: "vectors".to_string(),
                vector_segment_count: 2,
                native_memory_bytes: 64,
                model_cache_bytes: 16,
                quantization_cache_bytes: 8,
            })
            .unwrap();
        assert!(warmup.warmed);
        assert_eq!(warmup.vector_segment_count, 2);
        assert_eq!(warmup.native_memory_bytes, 64);
        assert_eq!(warmup.model_cache_bytes, 16);
        assert_eq!(warmup.quantization_cache_bytes, 8);
        assert_eq!(plugin.stats().graph_count, 2);
        assert_eq!(plugin.stats().warmed_index_count, 1);
        assert_eq!(plugin.stats().cache_entry_count, 1);
        assert_eq!(plugin.stats().native_memory_used_bytes, 64);
        assert_eq!(plugin.stats().native_memory_peak_bytes, 64);
        assert_eq!(plugin.stats().model_cache_used_bytes, 16);
        assert_eq!(plugin.stats().quantization_cache_used_bytes, 8);

        let cleared = plugin.clear_cache(KnnClearCacheRequest {
            index: "vectors".to_string(),
        });
        assert_eq!(cleared.cleared_entries, 1);
        assert_eq!(cleared.released_native_memory_bytes, 64);
        assert_eq!(cleared.released_model_cache_bytes, 16);
        assert_eq!(cleared.released_quantization_cache_bytes, 8);
        assert_eq!(plugin.stats().warmed_index_count, 0);
        assert_eq!(plugin.stats().cache_entry_count, 0);
        assert_eq!(plugin.stats().native_memory_used_bytes, 0);
        assert_eq!(plugin.stats().model_cache_used_bytes, 0);
        assert_eq!(plugin.stats().quantization_cache_used_bytes, 0);
        assert_eq!(plugin.stats().cache_evictions, 4);
    }

    #[test]
    fn plugin_apis_manage_model_training_get_search_and_delete() {
        let mut plugin = KnnPlugin::default();
        let method = KnnMethodDefinition {
            name: Some("hnsw".to_string()),
            engine: Some("faiss".to_string()),
            space_type: Some("l2".to_string()),
            parameters: BTreeMap::from([("m".to_string(), serde_json::json!(16))]),
        };

        let model = plugin
            .train_model(KnnModelTrainingRequest {
                model_id: "mini-lm-v1".to_string(),
                dimension: 384,
                method: method.clone(),
                training_index: "training-vectors".to_string(),
                training_field: "embedding".to_string(),
                metadata: BTreeMap::from([(
                    "description".to_string(),
                    serde_json::json!("MiniLM training fixture"),
                )]),
            })
            .unwrap();

        assert_eq!(model.state, KnnModelState::Trained);
        assert_eq!(plugin.get_model("mini-lm-v1").unwrap().method, method);
        assert_eq!(plugin.stats().model_count, 1);
        assert_eq!(plugin.stats().trained_model_count, 1);
        assert_eq!(plugin.stats().cache_entry_count, 1);

        let search = plugin.search_models(KnnModelSearchRequest {
            query: Some("MiniLM".to_string()),
            state: Some(KnnModelState::Trained),
            size: 10,
        });
        assert_eq!(search.total, 1);
        assert_eq!(search.models[0].model_id, "mini-lm-v1");

        let deleted = plugin.delete_model("mini-lm-v1").unwrap();
        assert_eq!(deleted.model_id, "mini-lm-v1");
        assert_eq!(plugin.stats().model_count, 0);
        assert_eq!(plugin.stats().cache_entry_count, 0);
        assert_eq!(
            plugin.get_model("mini-lm-v1").unwrap_err().to_string(),
            "k-NN model [mini-lm-v1] missing"
        );
    }

    #[test]
    fn operational_controls_enforce_memory_and_cache_limits() {
        let mut plugin = KnnPlugin::default();
        plugin.configure_operational_controls(KnnOperationalConfig {
            native_memory_limit_bytes: 10,
            model_cache_limit_bytes: 7,
            quantization_cache_limit_bytes: 5,
            simd_enabled: false,
            native_library_enabled: false,
            remote_index_build_enabled: false,
            rolling_restart_checks_enabled: true,
        });

        plugin.reserve_native_memory(6).unwrap();
        assert_eq!(plugin.operational_controls().native_memory.used_bytes, 6);
        assert_eq!(
            plugin.reserve_native_memory(5).unwrap_err().to_string(),
            "k-NN native memory request [5] exceeds limit [10]"
        );
        assert!(plugin.stats().circuit_breaker_triggered);
        plugin.release_native_memory(4);
        assert_eq!(plugin.operational_controls().native_memory.used_bytes, 2);

        assert_eq!(
            plugin
                .warmup(KnnWarmupRequest {
                    index: "too-large".to_string(),
                    vector_segment_count: 1,
                    native_memory_bytes: 9,
                    model_cache_bytes: 0,
                    quantization_cache_bytes: 0,
                })
                .unwrap_err()
                .to_string(),
            "k-NN native memory request [9] exceeds limit [10]"
        );
        assert_eq!(plugin.stats().warmed_index_count, 0);
        assert_eq!(plugin.operational_controls().native_memory.used_bytes, 2);

        plugin.record_model_cache_entry("model-a", 4);
        plugin.record_model_cache_entry("model-b", 4);
        let controls = plugin.operational_controls();
        assert_eq!(controls.model_cache.used_bytes, 4);
        assert_eq!(controls.model_cache.evictions, 1);
        assert!(controls.model_cache.entries.contains_key("model-b"));

        plugin.record_quantization_cache_entry("q-a", 3);
        plugin.record_quantization_cache_entry("q-b", 3);
        let controls = plugin.operational_controls();
        assert_eq!(controls.quantization_cache.used_bytes, 3);
        assert_eq!(controls.quantization_cache.evictions, 1);
    }

    #[test]
    fn operational_controls_report_feature_gates_and_remote_build_hooks() {
        let mut plugin = KnnPlugin::default();
        let mut config = KnnOperationalConfig::default();
        config.remote_index_build_enabled = true;
        plugin.configure_operational_controls(config.clone());

        let controls = plugin.operational_controls();
        assert_eq!(controls.feature_gates, KnnFeatureGates::compiled());
        assert_eq!(controls.config.remote_index_build_enabled, true);

        let request = KnnRemoteIndexBuildRequest {
            index: "vectors".to_string(),
            field: "embedding".to_string(),
            source_node: "node-a".to_string(),
            target_node: "node-b".to_string(),
            vector_count: 42,
        };
        let plan = plugin.plan_remote_index_build(request);
        if KnnFeatureGates::compiled().remote_index_build {
            let plan = plan.unwrap();
            assert_eq!(plan.state, KnnRemoteIndexBuildState::Planned);
            assert_eq!(plugin.operational_controls().remote_index_builds.len(), 1);
        } else {
            assert_eq!(
                plan.unwrap_err().to_string(),
                "k-NN feature [remote-index-build] is not enabled"
            );
        }

        let restart = plugin.rolling_restart_check(KnnRollingRestartCheckRequest {
            previous_feature_gates: KnnFeatureGates::compiled(),
            previous_config: config,
        });
        assert!(restart.compatible);
        assert_eq!(restart.reason, None);
    }

    #[test]
    fn compatibility_policy_keeps_lucene_jvm_bridge_out_of_hot_path() {
        let plugin = KnnPlugin::default();

        let decision = plugin
            .validate_hot_path_compatibility(KnnHotPathCompatibilityRequest::default())
            .unwrap();
        assert_eq!(decision.mode, KnnHotPathMode::RustNativeOnly);
        assert!(decision.offline_import_export_allowed);
        assert!(decision.later_data_node_compatibility_allowed);

        let error = plugin
            .validate_hot_path_compatibility(KnnHotPathCompatibilityRequest {
                lucene_jvm_bridge: true,
                dual_write: false,
                recovery_time_conversion: false,
                java_data_node_store_compatibility: false,
            })
            .unwrap_err();
        assert_eq!(
            error.to_string(),
            "Lucene/JVM bridge, dual-write, recovery-time conversion, and Java data-node store compatibility are not allowed in the k-NN hot path"
        );
    }
}
