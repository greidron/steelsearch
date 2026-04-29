//! ML Commons and neural-search model registry surface for Steelsearch.

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

pub const ML_COMMONS_PLUGIN_NAME: &str = "opensearch-ml";
pub const ML_MODEL_GROUP_RESOURCE: &str = "model_group";
pub const ML_MODEL_RESOURCE: &str = "model";
pub const ML_TASK_RESOURCE: &str = "task";

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct MlModelRegistry {
    model_groups: BTreeMap<String, MlModelGroup>,
    models: BTreeMap<String, MlModel>,
    connectors: BTreeMap<String, MlRemoteModelConnector>,
    tasks: BTreeMap<String, MlTask>,
    next_task_id: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MlModelGroup {
    pub group_id: String,
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    pub access: MlAccessControlMetadata,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MlAccessControlMetadata {
    pub owner: String,
    #[serde(default, skip_serializing_if = "BTreeSet::is_empty")]
    pub backend_roles: BTreeSet<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tenant: Option<String>,
    #[serde(default)]
    pub is_public: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MlAccessSubject {
    pub user: String,
    #[serde(default, skip_serializing_if = "BTreeSet::is_empty")]
    pub backend_roles: BTreeSet<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tenant: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MlModel {
    pub model_id: String,
    pub group_id: String,
    pub name: String,
    pub version: String,
    pub format: MlModelFormat,
    pub state: MlModelState,
    pub access: MlAccessControlMetadata,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub inference: Option<MlModelInferenceConfig>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub metadata: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum MlModelInferenceConfig {
    TextEmbedding(MlTextEmbeddingConfig),
    RemoteConnector(MlRemoteConnectorBinding),
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MlTextEmbeddingConfig {
    pub embedding_dimension: usize,
    pub max_sequence_length: usize,
    #[serde(default)]
    pub normalize: bool,
    #[serde(default)]
    pub pooling: MlTextEmbeddingPooling,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub model_content_hash: Option<String>,
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MlTextEmbeddingPooling {
    #[default]
    Mean,
    Cls,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MlRemoteConnectorBinding {
    pub connector_id: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub input_path: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub output_path: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MlRemoteModelConnector {
    pub connector_id: String,
    pub name: String,
    pub endpoint: String,
    pub protocol: MlRemoteConnectorProtocol,
    pub credential: MlCredentialReference,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub pre_processors: Vec<MlModelProcessor>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub post_processors: Vec<MlModelProcessor>,
    pub retry_policy: MlRetryPolicy,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rate_limit: Option<MlRateLimit>,
    pub timeout: MlTimeoutPolicy,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MlRemoteConnectorProtocol {
    HttpJson,
    AwsSigv4,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MlCredentialReference {
    pub credential_id: String,
    pub secure_setting_path: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MlModelProcessor {
    pub name: String,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub parameters: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MlRetryPolicy {
    pub max_attempts: u32,
    pub initial_backoff_millis: u64,
    pub max_backoff_millis: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MlRateLimit {
    pub requests_per_minute: u32,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub burst: Option<u32>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MlTimeoutPolicy {
    pub connect_timeout_millis: u64,
    pub request_timeout_millis: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MlModelFormat {
    Onnx,
    TorchScript,
    Remote,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MlModelState {
    Registered,
    Deploying,
    Deployed,
    Undeploying,
    Undeployed,
    Failed,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MlTask {
    pub task_id: String,
    pub kind: MlTaskKind,
    pub state: MlTaskState,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub model_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MlTaskKind {
    RegisterModel,
    DeployModel,
    UndeployModel,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MlTaskState {
    Created,
    Running,
    Completed,
    Failed,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CreateModelGroupRequest {
    pub group_id: String,
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    pub access: MlAccessControlMetadata,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RegisterModelRequest {
    pub model_id: String,
    pub group_id: String,
    pub name: String,
    pub version: String,
    pub format: MlModelFormat,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub access: Option<MlAccessControlMetadata>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub inference: Option<MlModelInferenceConfig>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub metadata: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CreateRemoteConnectorRequest {
    pub connector_id: String,
    pub name: String,
    pub endpoint: String,
    pub protocol: MlRemoteConnectorProtocol,
    pub credential: MlCredentialReference,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub pre_processors: Vec<MlModelProcessor>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub post_processors: Vec<MlModelProcessor>,
    pub retry_policy: MlRetryPolicy,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rate_limit: Option<MlRateLimit>,
    pub timeout: MlTimeoutPolicy,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MlRemoteInferencePlan {
    pub model_id: String,
    pub connector_id: String,
    pub endpoint: String,
    pub credential_id: String,
    pub pre_processor_names: Vec<String>,
    pub post_processor_names: Vec<String>,
    pub retry_policy: MlRetryPolicy,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rate_limit: Option<MlRateLimit>,
    pub timeout: MlTimeoutPolicy,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct TextEmbeddingRequest {
    pub model_id: String,
    pub texts: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct TextEmbeddingResponse {
    pub model_id: String,
    pub vectors: Vec<Vec<f32>>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct DenseVectorProcessorRequest {
    pub model_id: String,
    pub source_field: String,
    pub target_field: String,
    pub document: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct DenseVectorProcessorResponse {
    pub document: BTreeMap<String, Value>,
    pub vector: Vec<f32>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct SparseFeatureProcessorRequest {
    pub text: String,
    pub max_terms: usize,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct SparseFeature {
    pub term: String,
    pub weight: f32,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct RerankCandidate {
    pub id: String,
    pub text: String,
    #[serde(default)]
    pub lexical_score: f32,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct RerankProcessorRequest {
    pub query_text: String,
    pub candidates: Vec<RerankCandidate>,
    pub lexical_weight: f32,
    pub semantic_weight: f32,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct RerankScore {
    pub id: String,
    pub score: f32,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct HybridSearchInputRequest {
    pub model_id: String,
    pub query_text: String,
    pub sparse_max_terms: usize,
    pub lexical_weight: f32,
    pub vector_weight: f32,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct HybridSearchInput {
    pub query_text: String,
    pub dense_vector: Vec<f32>,
    pub sparse_features: Vec<SparseFeature>,
    pub lexical_weight: f32,
    pub vector_weight: f32,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SearchModelsRequest {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub group_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub state: Option<MlModelState>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum MlCommonsError {
    ModelGroupAlreadyExists(String),
    ModelGroupNotFound(String),
    ModelAlreadyExists(String),
    ModelNotFound(String),
    ConnectorAlreadyExists(String),
    ConnectorNotFound(String),
    TaskNotFound(String),
    AccessDenied(String),
    ModelNotDeployed(String),
    ProcessorInput(String),
    UnsupportedModelFormat {
        model_id: String,
        format: MlModelFormat,
        reason: String,
    },
    InvalidModelConfig(String),
}

impl fmt::Display for MlCommonsError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::ModelGroupAlreadyExists(group_id) => {
                write!(formatter, "model group [{group_id}] already exists")
            }
            Self::ModelGroupNotFound(group_id) => {
                write!(formatter, "model group [{group_id}] not found")
            }
            Self::ModelAlreadyExists(model_id) => {
                write!(formatter, "model [{model_id}] already exists")
            }
            Self::ModelNotFound(model_id) => write!(formatter, "model [{model_id}] not found"),
            Self::ConnectorAlreadyExists(connector_id) => {
                write!(formatter, "connector [{connector_id}] already exists")
            }
            Self::ConnectorNotFound(connector_id) => {
                write!(formatter, "connector [{connector_id}] not found")
            }
            Self::TaskNotFound(task_id) => write!(formatter, "task [{task_id}] not found"),
            Self::AccessDenied(resource) => write!(formatter, "access denied for [{resource}]"),
            Self::ModelNotDeployed(model_id) => {
                write!(formatter, "model [{model_id}] is not deployed")
            }
            Self::ProcessorInput(reason) => write!(formatter, "invalid processor input: {reason}"),
            Self::UnsupportedModelFormat {
                model_id,
                format,
                reason,
            } => write!(
                formatter,
                "model [{model_id}] format [{format:?}] is unsupported: {reason}"
            ),
            Self::InvalidModelConfig(reason) => write!(formatter, "invalid model config: {reason}"),
        }
    }
}

impl std::error::Error for MlCommonsError {}

impl MlModelRegistry {
    pub fn create_remote_connector(
        &mut self,
        request: CreateRemoteConnectorRequest,
    ) -> Result<MlRemoteModelConnector, MlCommonsError> {
        if self.connectors.contains_key(&request.connector_id) {
            return Err(MlCommonsError::ConnectorAlreadyExists(request.connector_id));
        }
        validate_remote_connector_request(&request)?;

        let connector = MlRemoteModelConnector {
            connector_id: request.connector_id.clone(),
            name: request.name,
            endpoint: request.endpoint,
            protocol: request.protocol,
            credential: request.credential,
            pre_processors: request.pre_processors,
            post_processors: request.post_processors,
            retry_policy: request.retry_policy,
            rate_limit: request.rate_limit,
            timeout: request.timeout,
        };
        self.connectors
            .insert(request.connector_id, connector.clone());
        Ok(connector)
    }

    pub fn create_model_group(
        &mut self,
        request: CreateModelGroupRequest,
    ) -> Result<MlModelGroup, MlCommonsError> {
        if self.model_groups.contains_key(&request.group_id) {
            return Err(MlCommonsError::ModelGroupAlreadyExists(request.group_id));
        }

        let group = MlModelGroup {
            group_id: request.group_id.clone(),
            name: request.name,
            description: request.description,
            access: request.access,
        };
        self.model_groups.insert(request.group_id, group.clone());
        Ok(group)
    }

    pub fn register_model(
        &mut self,
        request: RegisterModelRequest,
        subject: &MlAccessSubject,
    ) -> Result<(MlModel, MlTask), MlCommonsError> {
        if self.models.contains_key(&request.model_id) {
            return Err(MlCommonsError::ModelAlreadyExists(request.model_id));
        }

        let group = self
            .model_groups
            .get(&request.group_id)
            .ok_or_else(|| MlCommonsError::ModelGroupNotFound(request.group_id.clone()))?;
        ensure_access(&group.access, subject, &request.group_id)?;
        self.validate_model_inference_config(request.format, request.inference.as_ref())?;

        let model = MlModel {
            model_id: request.model_id.clone(),
            group_id: request.group_id,
            name: request.name,
            version: request.version,
            format: request.format,
            state: MlModelState::Registered,
            access: request.access.unwrap_or_else(|| group.access.clone()),
            inference: request.inference,
            metadata: request.metadata,
        };
        self.models.insert(request.model_id.clone(), model.clone());

        let task = self.completed_task(MlTaskKind::RegisterModel, Some(request.model_id));
        Ok((model, task))
    }

    pub fn deploy_model(
        &mut self,
        model_id: &str,
        subject: &MlAccessSubject,
    ) -> Result<MlTask, MlCommonsError> {
        let model = self
            .models
            .get_mut(model_id)
            .ok_or_else(|| MlCommonsError::ModelNotFound(model_id.to_string()))?;
        ensure_access(&model.access, subject, model_id)?;
        if model.format == MlModelFormat::TorchScript {
            return Err(MlCommonsError::UnsupportedModelFormat {
                model_id: model_id.to_string(),
                format: model.format,
                reason: "TorchScript serving is deferred behind an explicit bridge".to_string(),
            });
        }
        if let Some(MlModelInferenceConfig::RemoteConnector(binding)) = model.inference.as_ref() {
            if !self.connectors.contains_key(&binding.connector_id) {
                return Err(MlCommonsError::ConnectorNotFound(
                    binding.connector_id.clone(),
                ));
            }
        }

        model.state = MlModelState::Deploying;
        model.state = MlModelState::Deployed;
        Ok(self.completed_task(MlTaskKind::DeployModel, Some(model_id.to_string())))
    }

    pub fn undeploy_model(
        &mut self,
        model_id: &str,
        subject: &MlAccessSubject,
    ) -> Result<MlTask, MlCommonsError> {
        let model = self
            .models
            .get_mut(model_id)
            .ok_or_else(|| MlCommonsError::ModelNotFound(model_id.to_string()))?;
        ensure_access(&model.access, subject, model_id)?;

        model.state = MlModelState::Undeploying;
        model.state = MlModelState::Undeployed;
        Ok(self.completed_task(MlTaskKind::UndeployModel, Some(model_id.to_string())))
    }

    pub fn get_model(
        &self,
        model_id: &str,
        subject: &MlAccessSubject,
    ) -> Result<&MlModel, MlCommonsError> {
        let model = self
            .models
            .get(model_id)
            .ok_or_else(|| MlCommonsError::ModelNotFound(model_id.to_string()))?;
        ensure_access(&model.access, subject, model_id)?;
        Ok(model)
    }

    pub fn get_model_group(
        &self,
        group_id: &str,
        subject: &MlAccessSubject,
    ) -> Result<&MlModelGroup, MlCommonsError> {
        let group = self
            .model_groups
            .get(group_id)
            .ok_or_else(|| MlCommonsError::ModelGroupNotFound(group_id.to_string()))?;
        ensure_access(&group.access, subject, group_id)?;
        Ok(group)
    }

    pub fn get_task(&self, task_id: &str) -> Result<&MlTask, MlCommonsError> {
        self.tasks
            .get(task_id)
            .ok_or_else(|| MlCommonsError::TaskNotFound(task_id.to_string()))
    }

    pub fn get_remote_connector(
        &self,
        connector_id: &str,
    ) -> Result<&MlRemoteModelConnector, MlCommonsError> {
        self.connectors
            .get(connector_id)
            .ok_or_else(|| MlCommonsError::ConnectorNotFound(connector_id.to_string()))
    }

    pub fn search_models(
        &self,
        request: &SearchModelsRequest,
        subject: &MlAccessSubject,
    ) -> Vec<&MlModel> {
        self.models
            .values()
            .filter(|model| {
                request
                    .group_id
                    .as_deref()
                    .map_or(true, |id| model.group_id == id)
            })
            .filter(|model| {
                request
                    .name
                    .as_deref()
                    .map_or(true, |name| model.name == name)
            })
            .filter(|model| request.state.map_or(true, |state| model.state == state))
            .filter(|model| can_access(&model.access, subject))
            .collect()
    }

    pub fn embed_text(
        &self,
        request: TextEmbeddingRequest,
        subject: &MlAccessSubject,
    ) -> Result<TextEmbeddingResponse, MlCommonsError> {
        let model = self
            .models
            .get(&request.model_id)
            .ok_or_else(|| MlCommonsError::ModelNotFound(request.model_id.clone()))?;
        ensure_access(&model.access, subject, &request.model_id)?;

        if model.state != MlModelState::Deployed {
            return Err(MlCommonsError::ModelNotDeployed(request.model_id));
        }
        if model.format != MlModelFormat::Onnx {
            return Err(MlCommonsError::UnsupportedModelFormat {
                model_id: request.model_id,
                format: model.format,
                reason: "only ONNX text embedding models are supported in the native path"
                    .to_string(),
            });
        }

        let Some(MlModelInferenceConfig::TextEmbedding(config)) = model.inference.as_ref() else {
            return Err(MlCommonsError::InvalidModelConfig(
                "ONNX text embedding requires text embedding inference metadata".to_string(),
            ));
        };

        let vectors = request
            .texts
            .iter()
            .map(|text| embed_text_with_config(text, config))
            .collect();
        Ok(TextEmbeddingResponse {
            model_id: model.model_id.clone(),
            vectors,
        })
    }

    pub fn process_dense_vector(
        &self,
        request: DenseVectorProcessorRequest,
        subject: &MlAccessSubject,
    ) -> Result<DenseVectorProcessorResponse, MlCommonsError> {
        let Some(text) = request
            .document
            .get(&request.source_field)
            .and_then(Value::as_str)
        else {
            return Err(MlCommonsError::ProcessorInput(format!(
                "source field [{}] must be a string",
                request.source_field
            )));
        };

        let response = self.embed_text(
            TextEmbeddingRequest {
                model_id: request.model_id,
                texts: vec![text.to_string()],
            },
            subject,
        )?;
        let vector = response.vectors.into_iter().next().unwrap_or_default();
        let mut document = request.document;
        document.insert(request.target_field, vector_to_json(&vector));

        Ok(DenseVectorProcessorResponse { document, vector })
    }

    pub fn process_sparse_features(
        &self,
        request: SparseFeatureProcessorRequest,
    ) -> Result<Vec<SparseFeature>, MlCommonsError> {
        if request.max_terms == 0 {
            return Err(MlCommonsError::ProcessorInput(
                "max_terms must be greater than zero".to_string(),
            ));
        }
        Ok(sparse_features(&request.text, request.max_terms))
    }

    pub fn process_rerank_scores(
        &self,
        request: RerankProcessorRequest,
    ) -> Result<Vec<RerankScore>, MlCommonsError> {
        if request.lexical_weight < 0.0 || request.semantic_weight < 0.0 {
            return Err(MlCommonsError::ProcessorInput(
                "rerank weights must be non-negative".to_string(),
            ));
        }

        let query_features = sparse_feature_map(&request.query_text, usize::MAX);
        let mut scores: Vec<_> = request
            .candidates
            .iter()
            .map(|candidate| {
                let candidate_features = sparse_feature_map(&candidate.text, usize::MAX);
                let semantic_score = sparse_cosine(&query_features, &candidate_features);
                RerankScore {
                    id: candidate.id.clone(),
                    score: request.lexical_weight * candidate.lexical_score
                        + request.semantic_weight * semantic_score,
                }
            })
            .collect();
        scores.sort_by(|left, right| {
            right
                .score
                .partial_cmp(&left.score)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| left.id.cmp(&right.id))
        });
        Ok(scores)
    }

    pub fn build_hybrid_search_input(
        &self,
        request: HybridSearchInputRequest,
        subject: &MlAccessSubject,
    ) -> Result<HybridSearchInput, MlCommonsError> {
        if request.sparse_max_terms == 0 {
            return Err(MlCommonsError::ProcessorInput(
                "sparse_max_terms must be greater than zero".to_string(),
            ));
        }
        if request.lexical_weight < 0.0 || request.vector_weight < 0.0 {
            return Err(MlCommonsError::ProcessorInput(
                "hybrid weights must be non-negative".to_string(),
            ));
        }

        let dense_vector = self
            .embed_text(
                TextEmbeddingRequest {
                    model_id: request.model_id,
                    texts: vec![request.query_text.clone()],
                },
                subject,
            )?
            .vectors
            .into_iter()
            .next()
            .unwrap_or_default();

        Ok(HybridSearchInput {
            sparse_features: sparse_features(&request.query_text, request.sparse_max_terms),
            query_text: request.query_text,
            dense_vector,
            lexical_weight: request.lexical_weight,
            vector_weight: request.vector_weight,
        })
    }

    pub fn plan_remote_inference(
        &self,
        model_id: &str,
        subject: &MlAccessSubject,
    ) -> Result<MlRemoteInferencePlan, MlCommonsError> {
        let model = self
            .models
            .get(model_id)
            .ok_or_else(|| MlCommonsError::ModelNotFound(model_id.to_string()))?;
        ensure_access(&model.access, subject, model_id)?;
        if model.state != MlModelState::Deployed {
            return Err(MlCommonsError::ModelNotDeployed(model_id.to_string()));
        }
        if model.format != MlModelFormat::Remote {
            return Err(MlCommonsError::UnsupportedModelFormat {
                model_id: model_id.to_string(),
                format: model.format,
                reason: "remote inference planning requires a remote model".to_string(),
            });
        }

        let Some(MlModelInferenceConfig::RemoteConnector(binding)) = model.inference.as_ref()
        else {
            return Err(MlCommonsError::InvalidModelConfig(
                "remote model requires remote connector binding".to_string(),
            ));
        };
        let connector = self.get_remote_connector(&binding.connector_id)?;

        Ok(MlRemoteInferencePlan {
            model_id: model_id.to_string(),
            connector_id: connector.connector_id.clone(),
            endpoint: connector.endpoint.clone(),
            credential_id: connector.credential.credential_id.clone(),
            pre_processor_names: connector
                .pre_processors
                .iter()
                .map(|processor| processor.name.clone())
                .collect(),
            post_processor_names: connector
                .post_processors
                .iter()
                .map(|processor| processor.name.clone())
                .collect(),
            retry_policy: connector.retry_policy.clone(),
            rate_limit: connector.rate_limit.clone(),
            timeout: connector.timeout.clone(),
        })
    }

    fn completed_task(&mut self, kind: MlTaskKind, model_id: Option<String>) -> MlTask {
        self.next_task_id += 1;
        let task = MlTask {
            task_id: format!("ml-task-{}", self.next_task_id),
            kind,
            state: MlTaskState::Completed,
            model_id,
            error: None,
        };
        self.tasks.insert(task.task_id.clone(), task.clone());
        task
    }
    fn validate_model_inference_config(
        &self,
        format: MlModelFormat,
        inference: Option<&MlModelInferenceConfig>,
    ) -> Result<(), MlCommonsError> {
        match inference {
            Some(MlModelInferenceConfig::TextEmbedding(config)) => {
                if format != MlModelFormat::Onnx {
                    return Err(MlCommonsError::UnsupportedModelFormat {
                        model_id: "<registration>".to_string(),
                        format,
                        reason: "text embedding native serving currently accepts ONNX models only"
                            .to_string(),
                    });
                }
                if config.embedding_dimension == 0 {
                    return Err(MlCommonsError::InvalidModelConfig(
                        "embedding_dimension must be greater than zero".to_string(),
                    ));
                }
                if config.max_sequence_length == 0 {
                    return Err(MlCommonsError::InvalidModelConfig(
                        "max_sequence_length must be greater than zero".to_string(),
                    ));
                }
            }
            Some(MlModelInferenceConfig::RemoteConnector(binding)) => {
                if format != MlModelFormat::Remote {
                    return Err(MlCommonsError::UnsupportedModelFormat {
                        model_id: "<registration>".to_string(),
                        format,
                        reason: "remote connector binding requires remote model format".to_string(),
                    });
                }
                if !self.connectors.contains_key(&binding.connector_id) {
                    return Err(MlCommonsError::ConnectorNotFound(
                        binding.connector_id.clone(),
                    ));
                }
            }
            None => {}
        }
        Ok(())
    }
}

fn validate_remote_connector_request(
    request: &CreateRemoteConnectorRequest,
) -> Result<(), MlCommonsError> {
    if request.endpoint.trim().is_empty() {
        return Err(MlCommonsError::InvalidModelConfig(
            "remote connector endpoint must not be empty".to_string(),
        ));
    }
    if request.credential.credential_id.trim().is_empty()
        || request.credential.secure_setting_path.trim().is_empty()
    {
        return Err(MlCommonsError::InvalidModelConfig(
            "remote connector credentials must reference secure settings".to_string(),
        ));
    }
    if request.retry_policy.max_attempts == 0 {
        return Err(MlCommonsError::InvalidModelConfig(
            "retry max_attempts must be greater than zero".to_string(),
        ));
    }
    if request.timeout.connect_timeout_millis == 0 || request.timeout.request_timeout_millis == 0 {
        return Err(MlCommonsError::InvalidModelConfig(
            "remote connector timeouts must be greater than zero".to_string(),
        ));
    }
    if matches!(
        request
            .rate_limit
            .as_ref()
            .map(|limit| limit.requests_per_minute),
        Some(0)
    ) {
        return Err(MlCommonsError::InvalidModelConfig(
            "rate limit requests_per_minute must be greater than zero".to_string(),
        ));
    }
    Ok(())
}

fn embed_text_with_config(text: &str, config: &MlTextEmbeddingConfig) -> Vec<f32> {
    let mut vector = vec![0.0; config.embedding_dimension];
    let mut seen = 0usize;

    for token in text.split_whitespace().take(config.max_sequence_length) {
        let hash = stable_hash(token.as_bytes());
        let index = hash as usize % config.embedding_dimension;
        let sign = if hash & 1 == 0 { 1.0 } else { -1.0 };
        vector[index] += sign;
        seen += 1;
    }

    if seen == 0 {
        let index = stable_hash(text.as_bytes()) as usize % config.embedding_dimension;
        vector[index] = 1.0;
        seen = 1;
    }

    if config.pooling == MlTextEmbeddingPooling::Mean {
        let divisor = seen as f32;
        for value in &mut vector {
            *value /= divisor;
        }
    }

    if config.normalize {
        let norm = vector.iter().map(|value| value * value).sum::<f32>().sqrt();
        if norm > 0.0 {
            for value in &mut vector {
                *value /= norm;
            }
        }
    }

    vector
}

fn vector_to_json(vector: &[f32]) -> Value {
    Value::Array(vector.iter().map(|value| json!(value)).collect())
}

fn sparse_features(text: &str, max_terms: usize) -> Vec<SparseFeature> {
    let mut features: Vec<_> = sparse_feature_map(text, max_terms)
        .into_iter()
        .map(|(term, weight)| SparseFeature { term, weight })
        .collect();
    features.sort_by(|left, right| {
        right
            .weight
            .partial_cmp(&left.weight)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| left.term.cmp(&right.term))
    });
    features.truncate(max_terms);
    features
}

fn sparse_feature_map(text: &str, max_terms: usize) -> BTreeMap<String, f32> {
    let mut counts = BTreeMap::new();
    let mut total = 0.0f32;
    for token in normalized_tokens(text) {
        *counts.entry(token).or_insert(0.0) += 1.0;
        total += 1.0;
    }
    if total == 0.0 {
        return BTreeMap::new();
    }

    let mut weighted: Vec<_> = counts
        .into_iter()
        .map(|(term, count)| (term, count / total))
        .collect();
    weighted.sort_by(|left, right| {
        right
            .1
            .partial_cmp(&left.1)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| left.0.cmp(&right.0))
    });
    weighted.truncate(max_terms);
    weighted.into_iter().collect()
}

fn normalized_tokens(text: &str) -> impl Iterator<Item = String> + '_ {
    text.split_whitespace()
        .map(|token| {
            token
                .trim_matches(|character: char| !character.is_alphanumeric())
                .to_ascii_lowercase()
        })
        .filter(|token| !token.is_empty())
}

fn sparse_cosine(left: &BTreeMap<String, f32>, right: &BTreeMap<String, f32>) -> f32 {
    let dot = left
        .iter()
        .map(|(term, left_weight)| left_weight * right.get(term).copied().unwrap_or_default())
        .sum::<f32>();
    let left_norm = left
        .values()
        .map(|weight| weight * weight)
        .sum::<f32>()
        .sqrt();
    let right_norm = right
        .values()
        .map(|weight| weight * weight)
        .sum::<f32>()
        .sqrt();
    if left_norm == 0.0 || right_norm == 0.0 {
        0.0
    } else {
        dot / (left_norm * right_norm)
    }
}

fn stable_hash(bytes: &[u8]) -> u64 {
    let mut hash = 0xcbf29ce484222325u64;
    for byte in bytes {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x100000001b3);
    }
    hash
}

pub fn can_access(access: &MlAccessControlMetadata, subject: &MlAccessSubject) -> bool {
    if access.is_public || access.owner == subject.user {
        return tenant_matches(access, subject);
    }

    access
        .backend_roles
        .iter()
        .any(|role| subject.backend_roles.contains(role))
        && tenant_matches(access, subject)
}

fn tenant_matches(access: &MlAccessControlMetadata, subject: &MlAccessSubject) -> bool {
    access.tenant.is_none() || access.tenant == subject.tenant
}

fn ensure_access(
    access: &MlAccessControlMetadata,
    subject: &MlAccessSubject,
    resource: &str,
) -> Result<(), MlCommonsError> {
    can_access(access, subject)
        .then_some(())
        .ok_or_else(|| MlCommonsError::AccessDenied(resource.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn registry_creates_group_and_registers_model_with_metadata_and_access() {
        let mut registry = MlModelRegistry::default();
        let owner = subject("alice", ["ml-admin"], Some("tenant-a"));

        let group = registry
            .create_model_group(CreateModelGroupRequest {
                group_id: "group-1".to_string(),
                name: "sentence-transformers".to_string(),
                description: Some("embedding models".to_string()),
                access: access("alice", ["ml-admin"], Some("tenant-a"), false),
            })
            .unwrap();
        assert_eq!(group.name, "sentence-transformers");

        let (model, task) = registry
            .register_model(
                RegisterModelRequest {
                    model_id: "model-1".to_string(),
                    group_id: "group-1".to_string(),
                    name: "all-MiniLM-L6-v2".to_string(),
                    version: "1".to_string(),
                    format: MlModelFormat::Onnx,
                    access: None,
                    inference: None,
                    metadata: BTreeMap::from([("embedding_dimension".to_string(), json!(384))]),
                },
                &owner,
            )
            .unwrap();

        assert_eq!(model.state, MlModelState::Registered);
        assert_eq!(model.access.owner, "alice");
        assert_eq!(model.metadata["embedding_dimension"], json!(384));
        assert_eq!(task.kind, MlTaskKind::RegisterModel);
        assert_eq!(task.state, MlTaskState::Completed);
        assert_eq!(registry.get_task(&task.task_id).unwrap(), &task);
    }

    #[test]
    fn deploy_and_undeploy_update_model_state_and_complete_tasks() {
        let mut registry = registry_with_model();
        let owner = subject("alice", ["ml-admin"], Some("tenant-a"));

        let deploy_task = registry.deploy_model("model-1", &owner).unwrap();
        assert_eq!(deploy_task.kind, MlTaskKind::DeployModel);
        assert_eq!(
            registry.get_model("model-1", &owner).unwrap().state,
            MlModelState::Deployed
        );

        let undeploy_task = registry.undeploy_model("model-1", &owner).unwrap();
        assert_eq!(undeploy_task.kind, MlTaskKind::UndeployModel);
        assert_eq!(
            registry.get_model("model-1", &owner).unwrap().state,
            MlModelState::Undeployed
        );
    }

    #[test]
    fn access_control_rejects_unmatched_subject() {
        let registry = registry_with_model();
        let stranger = subject("bob", ["analytics"], Some("tenant-a"));

        let error = registry.get_model("model-1", &stranger).unwrap_err();
        assert_eq!(error, MlCommonsError::AccessDenied("model-1".to_string()));
        assert!(registry
            .search_models(&SearchModelsRequest::default(), &stranger)
            .is_empty());
    }

    #[test]
    fn public_access_still_honors_tenant_boundary() {
        let public_tenant_access = access("alice", [], Some("tenant-a"), true);
        assert!(can_access(
            &public_tenant_access,
            &subject("bob", [], Some("tenant-a"))
        ));
        assert!(!can_access(
            &public_tenant_access,
            &subject("bob", [], Some("tenant-b"))
        ));
    }

    #[test]
    fn deployed_onnx_text_embedding_model_returns_vectors() {
        let mut registry = MlModelRegistry::default();
        let owner = subject("alice", ["ml-admin"], Some("tenant-a"));
        registry
            .create_model_group(CreateModelGroupRequest {
                group_id: "group-1".to_string(),
                name: "embeddings".to_string(),
                description: None,
                access: access("alice", ["ml-admin"], Some("tenant-a"), false),
            })
            .unwrap();
        registry
            .register_model(
                RegisterModelRequest {
                    model_id: "minilm-onnx".to_string(),
                    group_id: "group-1".to_string(),
                    name: "all-MiniLM-L6-v2".to_string(),
                    version: "1".to_string(),
                    format: MlModelFormat::Onnx,
                    access: None,
                    inference: Some(MlModelInferenceConfig::TextEmbedding(
                        MlTextEmbeddingConfig {
                            embedding_dimension: 8,
                            max_sequence_length: 16,
                            normalize: true,
                            pooling: MlTextEmbeddingPooling::Mean,
                            model_content_hash: Some("sha256:test".to_string()),
                        },
                    )),
                    metadata: BTreeMap::new(),
                },
                &owner,
            )
            .unwrap();
        registry.deploy_model("minilm-onnx", &owner).unwrap();

        let response = registry
            .embed_text(
                TextEmbeddingRequest {
                    model_id: "minilm-onnx".to_string(),
                    texts: vec!["steelsearch vector search".to_string()],
                },
                &owner,
            )
            .unwrap();

        assert_eq!(response.model_id, "minilm-onnx");
        assert_eq!(response.vectors.len(), 1);
        assert_eq!(response.vectors[0].len(), 8);
        let norm = response.vectors[0]
            .iter()
            .map(|value| value * value)
            .sum::<f32>()
            .sqrt();
        assert!((norm - 1.0).abs() < 0.0001);
    }

    #[test]
    fn minilm_compatible_embed_text_is_deterministic_normalized_and_repeatable() {
        let (registry, owner) = registry_with_deployed_embedding_model();
        let request = TextEmbeddingRequest {
            model_id: "minilm-onnx".to_string(),
            texts: vec![
                "steelsearch vector search".to_string(),
                "rust vector search".to_string(),
                "steelsearch vector search".to_string(),
            ],
        };

        let first = registry.embed_text(request.clone(), &owner).unwrap();
        let second = registry.embed_text(request.clone(), &owner).unwrap();

        assert_eq!(first.model_id, "minilm-onnx");
        assert_eq!(first.vectors, second.vectors);
        assert_eq!(first.vectors.len(), request.texts.len());
        assert_eq!(first.vectors[0], first.vectors[2]);

        for vector in &first.vectors {
            assert_eq!(vector.len(), 8);
            assert!(vector.iter().all(|value| value.is_finite()));
            let norm = vector.iter().map(|value| value * value).sum::<f32>().sqrt();
            assert!((norm - 1.0).abs() < 0.0001);
        }

        let reversed = registry
            .embed_text(
                TextEmbeddingRequest {
                    model_id: "minilm-onnx".to_string(),
                    texts: vec![
                        "rust vector search".to_string(),
                        "steelsearch vector search".to_string(),
                    ],
                },
                &owner,
            )
            .unwrap();
        assert_eq!(reversed.vectors[0], first.vectors[1]);
        assert_eq!(reversed.vectors[1], first.vectors[0]);
    }

    #[test]
    fn torchscript_embedding_serving_is_deferred() {
        let mut registry = MlModelRegistry::default();
        let owner = subject("alice", ["ml-admin"], Some("tenant-a"));
        registry
            .create_model_group(CreateModelGroupRequest {
                group_id: "group-1".to_string(),
                name: "embeddings".to_string(),
                description: None,
                access: access("alice", ["ml-admin"], Some("tenant-a"), false),
            })
            .unwrap();
        registry
            .register_model(
                RegisterModelRequest {
                    model_id: "minilm-torch".to_string(),
                    group_id: "group-1".to_string(),
                    name: "all-MiniLM-L6-v2".to_string(),
                    version: "1".to_string(),
                    format: MlModelFormat::TorchScript,
                    access: None,
                    inference: None,
                    metadata: BTreeMap::new(),
                },
                &owner,
            )
            .unwrap();

        let error = registry.deploy_model("minilm-torch", &owner).unwrap_err();
        assert!(matches!(
            error,
            MlCommonsError::UnsupportedModelFormat {
                format: MlModelFormat::TorchScript,
                ..
            }
        ));
    }

    #[test]
    fn remote_connector_stores_policy_and_plans_inference() {
        let mut registry = MlModelRegistry::default();
        let owner = subject("alice", ["ml-admin"], Some("tenant-a"));
        let connector = registry
            .create_remote_connector(remote_connector_request("connector-1"))
            .unwrap();
        assert_eq!(
            connector.credential.secure_setting_path,
            "ml.remote.api_key"
        );
        assert_eq!(connector.retry_policy.max_attempts, 3);

        registry
            .create_model_group(CreateModelGroupRequest {
                group_id: "group-1".to_string(),
                name: "remote".to_string(),
                description: None,
                access: access("alice", ["ml-admin"], Some("tenant-a"), false),
            })
            .unwrap();
        registry
            .register_model(
                RegisterModelRequest {
                    model_id: "remote-model".to_string(),
                    group_id: "group-1".to_string(),
                    name: "hosted-embedding".to_string(),
                    version: "1".to_string(),
                    format: MlModelFormat::Remote,
                    access: None,
                    inference: Some(MlModelInferenceConfig::RemoteConnector(
                        MlRemoteConnectorBinding {
                            connector_id: "connector-1".to_string(),
                            input_path: Some("$.text".to_string()),
                            output_path: Some("$.embedding".to_string()),
                        },
                    )),
                    metadata: BTreeMap::new(),
                },
                &owner,
            )
            .unwrap();
        registry.deploy_model("remote-model", &owner).unwrap();

        let plan = registry
            .plan_remote_inference("remote-model", &owner)
            .unwrap();
        assert_eq!(plan.model_id, "remote-model");
        assert_eq!(plan.connector_id, "connector-1");
        assert_eq!(plan.endpoint, "https://models.example.test/embed");
        assert_eq!(plan.credential_id, "cred-1");
        assert_eq!(plan.pre_processor_names, vec!["template_request"]);
        assert_eq!(plan.post_processor_names, vec!["extract_embedding"]);
        assert_eq!(plan.retry_policy.max_attempts, 3);
        assert_eq!(plan.retry_policy.initial_backoff_millis, 100);
        assert_eq!(plan.retry_policy.max_backoff_millis, 1_000);
        let rate_limit = plan.rate_limit.as_ref().unwrap();
        assert_eq!(rate_limit.requests_per_minute, 120);
        assert_eq!(rate_limit.burst, Some(10));
        assert_eq!(plan.timeout.connect_timeout_millis, 1_000);
        assert_eq!(plan.timeout.request_timeout_millis, 30_000);

        let response = serde_json::to_value(&plan).unwrap();
        assert_eq!(response["credential_id"], "cred-1");
        assert!(response.get("credential").is_none());
        assert!(response.get("secure_setting_path").is_none());
        assert!(response.get("pre_processors").is_none());
        assert!(response.get("post_processors").is_none());
        let response_text = response.to_string();
        assert!(!response_text.contains("ml.remote.api_key"));
        assert!(!response_text.contains("$.text"));
        assert!(!response_text.contains("$.embedding"));
    }

    #[test]
    fn remote_connector_validation_rejects_missing_credentials() {
        let mut request = remote_connector_request("connector-1");
        request.credential.secure_setting_path.clear();

        let error = MlModelRegistry::default()
            .create_remote_connector(request)
            .unwrap_err();
        assert!(matches!(error, MlCommonsError::InvalidModelConfig(_)));
    }

    #[test]
    fn dense_vector_processor_embeds_document_field() {
        let (registry, owner) = registry_with_deployed_embedding_model();
        let document = BTreeMap::from([
            ("body".to_string(), json!("steelsearch vector pipeline")),
            ("tenant".to_string(), json!("development")),
            ("views".to_string(), json!(3)),
        ]);
        let response = registry
            .process_dense_vector(
                DenseVectorProcessorRequest {
                    model_id: "minilm-onnx".to_string(),
                    source_field: "body".to_string(),
                    target_field: "body_vector".to_string(),
                    document: document.clone(),
                },
                &owner,
            )
            .unwrap();

        assert_eq!(response.vector.len(), 8);
        assert_eq!(response.document["body"], document["body"]);
        assert_eq!(response.document["tenant"], document["tenant"]);
        assert_eq!(response.document["views"], document["views"]);
        assert!(response.document.contains_key("body_vector"));
        let vector_field = response.document["body_vector"].as_array().unwrap();
        assert_eq!(vector_field.len(), response.vector.len());
        assert_eq!(
            vector_field
                .iter()
                .map(|value| value.as_f64().unwrap() as f32)
                .collect::<Vec<_>>(),
            response.vector
        );

        let missing_source = registry
            .process_dense_vector(
                DenseVectorProcessorRequest {
                    model_id: "minilm-onnx".to_string(),
                    source_field: "missing".to_string(),
                    target_field: "missing_vector".to_string(),
                    document: document.clone(),
                },
                &owner,
            )
            .unwrap_err();
        assert_eq!(
            missing_source,
            MlCommonsError::ProcessorInput("source field [missing] must be a string".to_string())
        );

        let non_string_source = registry
            .process_dense_vector(
                DenseVectorProcessorRequest {
                    model_id: "minilm-onnx".to_string(),
                    source_field: "views".to_string(),
                    target_field: "views_vector".to_string(),
                    document,
                },
                &owner,
            )
            .unwrap_err();
        assert_eq!(
            non_string_source,
            MlCommonsError::ProcessorInput("source field [views] must be a string".to_string())
        );
    }

    #[test]
    fn sparse_feature_and_rerank_processors_produce_ranked_inputs() {
        let registry = MlModelRegistry::default();
        let features = registry
            .process_sparse_features(SparseFeatureProcessorRequest {
                text: "vector search vector rust".to_string(),
                max_terms: 2,
            })
            .unwrap();
        assert_eq!(features[0].term, "vector");
        assert_eq!(features.len(), 2);

        let scores = registry
            .process_rerank_scores(RerankProcessorRequest {
                query_text: "rust vector search".to_string(),
                candidates: vec![
                    RerankCandidate {
                        id: "doc-1".to_string(),
                        text: "rust vector search engine".to_string(),
                        lexical_score: 0.2,
                    },
                    RerankCandidate {
                        id: "doc-2".to_string(),
                        text: "unrelated document".to_string(),
                        lexical_score: 0.9,
                    },
                ],
                lexical_weight: 0.2,
                semantic_weight: 0.8,
            })
            .unwrap();

        assert_eq!(scores[0].id, "doc-1");
        assert!(scores[0].score > scores[1].score);
    }

    #[test]
    fn hybrid_search_input_combines_sparse_and_dense_query_inputs() {
        let (registry, owner) = registry_with_deployed_embedding_model();
        let input = registry
            .build_hybrid_search_input(
                HybridSearchInputRequest {
                    model_id: "minilm-onnx".to_string(),
                    query_text: "hybrid vector search".to_string(),
                    sparse_max_terms: 3,
                    lexical_weight: 0.4,
                    vector_weight: 0.6,
                },
                &owner,
            )
            .unwrap();

        assert_eq!(input.query_text, "hybrid vector search");
        assert_eq!(input.dense_vector.len(), 8);
        assert_eq!(input.sparse_features.len(), 3);
        assert_eq!(input.lexical_weight, 0.4);
        assert_eq!(input.vector_weight, 0.6);
        assert_eq!(input.sparse_features[0].term, "hybrid");
        assert_eq!(input.sparse_features[1].term, "search");
        assert_eq!(input.sparse_features[2].term, "vector");

        let direct_embedding = registry
            .embed_text(
                TextEmbeddingRequest {
                    model_id: "minilm-onnx".to_string(),
                    texts: vec!["hybrid vector search".to_string()],
                },
                &owner,
            )
            .unwrap();
        assert_eq!(input.dense_vector, direct_embedding.vectors[0]);

        let zero_terms = registry
            .build_hybrid_search_input(
                HybridSearchInputRequest {
                    model_id: "minilm-onnx".to_string(),
                    query_text: "hybrid vector search".to_string(),
                    sparse_max_terms: 0,
                    lexical_weight: 0.4,
                    vector_weight: 0.6,
                },
                &owner,
            )
            .unwrap_err();
        assert_eq!(
            zero_terms,
            MlCommonsError::ProcessorInput(
                "sparse_max_terms must be greater than zero".to_string()
            )
        );

        let negative_weight = registry
            .build_hybrid_search_input(
                HybridSearchInputRequest {
                    model_id: "minilm-onnx".to_string(),
                    query_text: "hybrid vector search".to_string(),
                    sparse_max_terms: 3,
                    lexical_weight: -0.1,
                    vector_weight: 0.6,
                },
                &owner,
            )
            .unwrap_err();
        assert_eq!(
            negative_weight,
            MlCommonsError::ProcessorInput("hybrid weights must be non-negative".to_string())
        );
    }

    #[test]
    fn minilm_compatible_end_to_end_embedding_knn_and_hybrid_flow() {
        let (registry, owner) = registry_with_deployed_embedding_model();
        assert_eq!(
            registry.get_model("minilm-onnx", &owner).unwrap().state,
            MlModelState::Deployed
        );

        let raw_docs = [
            ("doc-rust", "rust vector search"),
            ("doc-java", "java transport compatibility"),
            ("doc-cooking", "recipe tomatoes pasta"),
        ];
        let mut docs = Vec::new();
        for (id, body) in raw_docs {
            let processed = registry
                .process_dense_vector(
                    DenseVectorProcessorRequest {
                        model_id: "minilm-onnx".to_string(),
                        source_field: "body".to_string(),
                        target_field: "body_vector".to_string(),
                        document: BTreeMap::from([("body".to_string(), json!(body))]),
                    },
                    &owner,
                )
                .unwrap();
            docs.push((id.to_string(), body.to_string(), processed.vector));
        }

        let query = registry
            .build_hybrid_search_input(
                HybridSearchInputRequest {
                    model_id: "minilm-onnx".to_string(),
                    query_text: "rust vector search".to_string(),
                    sparse_max_terms: 8,
                    lexical_weight: 0.5,
                    vector_weight: 0.5,
                },
                &owner,
            )
            .unwrap();

        let mut knn_hits: Vec<_> = docs
            .iter()
            .map(|(id, _, vector)| (id.clone(), vector_cosine(&query.dense_vector, vector)))
            .collect();
        knn_hits.sort_by(|left, right| right.1.partial_cmp(&left.1).unwrap());
        assert_eq!(knn_hits[0].0, "doc-rust");

        let query_sparse: BTreeMap<_, _> = query
            .sparse_features
            .iter()
            .map(|feature| (feature.term.clone(), feature.weight))
            .collect();
        let mut hybrid_hits: Vec<_> = docs
            .iter()
            .map(|(id, body, vector)| {
                let doc_sparse = sparse_feature_map(body, 8);
                let lexical = sparse_cosine(&query_sparse, &doc_sparse);
                let vector_score = vector_cosine(&query.dense_vector, vector);
                (
                    id.clone(),
                    query.lexical_weight * lexical + query.vector_weight * vector_score,
                )
            })
            .collect();
        hybrid_hits.sort_by(|left, right| right.1.partial_cmp(&left.1).unwrap());
        assert_eq!(hybrid_hits[0].0, "doc-rust");

        let rerank_scores = registry
            .process_rerank_scores(RerankProcessorRequest {
                query_text: query.query_text,
                candidates: docs
                    .iter()
                    .map(|(id, body, _)| RerankCandidate {
                        id: id.clone(),
                        text: body.clone(),
                        lexical_score: 0.0,
                    })
                    .collect(),
                lexical_weight: 0.0,
                semantic_weight: 1.0,
            })
            .unwrap();
        assert_eq!(rerank_scores[0].id, "doc-rust");
    }

    fn registry_with_model() -> MlModelRegistry {
        let mut registry = MlModelRegistry::default();
        let owner = subject("alice", ["ml-admin"], Some("tenant-a"));
        registry
            .create_model_group(CreateModelGroupRequest {
                group_id: "group-1".to_string(),
                name: "group".to_string(),
                description: None,
                access: access("alice", ["ml-admin"], Some("tenant-a"), false),
            })
            .unwrap();
        registry
            .register_model(
                RegisterModelRequest {
                    model_id: "model-1".to_string(),
                    group_id: "group-1".to_string(),
                    name: "all-MiniLM-L6-v2".to_string(),
                    version: "1".to_string(),
                    format: MlModelFormat::Onnx,
                    access: None,
                    inference: None,
                    metadata: BTreeMap::new(),
                },
                &owner,
            )
            .unwrap();
        registry
    }

    fn registry_with_deployed_embedding_model() -> (MlModelRegistry, MlAccessSubject) {
        let mut registry = MlModelRegistry::default();
        let owner = subject("alice", ["ml-admin"], Some("tenant-a"));
        registry
            .create_model_group(CreateModelGroupRequest {
                group_id: "group-1".to_string(),
                name: "embeddings".to_string(),
                description: None,
                access: access("alice", ["ml-admin"], Some("tenant-a"), false),
            })
            .unwrap();
        registry
            .register_model(
                RegisterModelRequest {
                    model_id: "minilm-onnx".to_string(),
                    group_id: "group-1".to_string(),
                    name: "all-MiniLM-L6-v2".to_string(),
                    version: "1".to_string(),
                    format: MlModelFormat::Onnx,
                    access: None,
                    inference: Some(MlModelInferenceConfig::TextEmbedding(
                        MlTextEmbeddingConfig {
                            embedding_dimension: 8,
                            max_sequence_length: 16,
                            normalize: true,
                            pooling: MlTextEmbeddingPooling::Mean,
                            model_content_hash: Some("sha256:test".to_string()),
                        },
                    )),
                    metadata: BTreeMap::new(),
                },
                &owner,
            )
            .unwrap();
        registry.deploy_model("minilm-onnx", &owner).unwrap();
        (registry, owner)
    }

    fn access<const N: usize>(
        owner: &str,
        roles: [&str; N],
        tenant: Option<&str>,
        is_public: bool,
    ) -> MlAccessControlMetadata {
        MlAccessControlMetadata {
            owner: owner.to_string(),
            backend_roles: roles.into_iter().map(str::to_string).collect(),
            tenant: tenant.map(str::to_string),
            is_public,
        }
    }

    fn subject<const N: usize>(
        user: &str,
        roles: [&str; N],
        tenant: Option<&str>,
    ) -> MlAccessSubject {
        MlAccessSubject {
            user: user.to_string(),
            backend_roles: roles.into_iter().map(str::to_string).collect(),
            tenant: tenant.map(str::to_string),
        }
    }

    fn vector_cosine(left: &[f32], right: &[f32]) -> f32 {
        let dot = left
            .iter()
            .zip(right)
            .map(|(left, right)| left * right)
            .sum::<f32>();
        let left_norm = left.iter().map(|value| value * value).sum::<f32>().sqrt();
        let right_norm = right.iter().map(|value| value * value).sum::<f32>().sqrt();
        if left_norm == 0.0 || right_norm == 0.0 {
            0.0
        } else {
            dot / (left_norm * right_norm)
        }
    }

    fn remote_connector_request(connector_id: &str) -> CreateRemoteConnectorRequest {
        CreateRemoteConnectorRequest {
            connector_id: connector_id.to_string(),
            name: "hosted model".to_string(),
            endpoint: "https://models.example.test/embed".to_string(),
            protocol: MlRemoteConnectorProtocol::HttpJson,
            credential: MlCredentialReference {
                credential_id: "cred-1".to_string(),
                secure_setting_path: "ml.remote.api_key".to_string(),
            },
            pre_processors: vec![MlModelProcessor {
                name: "template_request".to_string(),
                parameters: BTreeMap::from([("input".to_string(), json!("$.text"))]),
            }],
            post_processors: vec![MlModelProcessor {
                name: "extract_embedding".to_string(),
                parameters: BTreeMap::from([("path".to_string(), json!("$.embedding"))]),
            }],
            retry_policy: MlRetryPolicy {
                max_attempts: 3,
                initial_backoff_millis: 100,
                max_backoff_millis: 1_000,
            },
            rate_limit: Some(MlRateLimit {
                requests_per_minute: 120,
                burst: Some(10),
            }),
            timeout: MlTimeoutPolicy {
                connect_timeout_millis: 1_000,
                request_timeout_millis: 30_000,
            },
        }
    }
}
