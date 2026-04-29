//! OpenSearch-to-Steelsearch migration inventory reader.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct MigrationSourceInventory {
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub indices: BTreeMap<String, SourceIndexMetadata>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub legacy_templates: BTreeMap<String, Value>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub index_templates: BTreeMap<String, Value>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub component_templates: BTreeMap<String, Value>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub ingest_pipelines: BTreeMap<String, Value>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub data_streams: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SourceIndexMetadata {
    pub name: String,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub settings: BTreeMap<String, Value>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub mappings: BTreeMap<String, Value>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub aliases: BTreeMap<String, Value>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub state: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub uuid: Option<String>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub raw_metadata: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DocumentExportRequest {
    pub index: String,
    pub mode: DocumentExportMode,
    pub page_size: u32,
    pub slices: u32,
    pub retry: RetryPolicy,
    pub throttle: ThrottlePolicy,
    pub backoff: BackoffPolicy,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub checkpoint: Option<ExportCheckpoint>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DocumentExportMode {
    Scroll { keep_alive: String },
    PitSearchAfter { pit_keep_alive: String },
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RetryPolicy {
    pub max_attempts: u32,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ThrottlePolicy {
    pub requests_per_second: u32,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct BackoffPolicy {
    pub initial_millis: u64,
    pub max_millis: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ExportCheckpoint {
    pub index: String,
    pub slice_id: u32,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub scroll_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub pit_id: Option<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub search_after: Vec<Value>,
    pub exported_documents: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DocumentExportPlan {
    pub index: String,
    pub mode: DocumentExportMode,
    pub page_size: u32,
    pub slices: Vec<DocumentExportSlice>,
    pub retry: RetryPolicy,
    pub throttle: ThrottlePolicy,
    pub backoff: BackoffPolicy,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DocumentExportSlice {
    pub slice_id: u32,
    pub max_slices: u32,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub resume: Option<ExportCheckpoint>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct BulkImportRequest {
    pub target_index: String,
    pub batch_size: usize,
    pub max_concurrency: usize,
    pub max_in_flight_batches: usize,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub checkpoint: Option<BulkImportCheckpoint>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct BulkImportDocument {
    pub source_index: String,
    pub target_index: String,
    pub id: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub routing: Option<String>,
    pub source: Value,
    pub exported_sequence: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct BulkImportPlan {
    pub target_index: String,
    pub batch_size: usize,
    pub max_concurrency: usize,
    pub max_in_flight_batches: usize,
    pub batches: Vec<BulkImportBatch>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub resume_from: Option<BulkImportCheckpoint>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct BulkImportBatch {
    pub batch_id: u64,
    pub operations: Vec<BulkOperation>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct BulkOperation {
    pub op_type: BulkOperationType,
    pub source_index: String,
    pub target_index: String,
    pub id: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub routing: Option<String>,
    pub source: Value,
    pub exported_sequence: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BulkOperationType {
    Index,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct BulkImportCheckpoint {
    pub target_index: String,
    pub last_exported_sequence: u64,
    pub imported_documents: u64,
    pub failed_documents: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct BulkItemFailure {
    pub target_index: String,
    pub id: String,
    pub status: u16,
    pub error_type: String,
    pub reason: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub document: Option<BulkImportDocument>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DeadLetterRecord {
    pub target_index: String,
    pub id: String,
    pub reason: String,
    pub source: Value,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SteelsearchIndexDefinition {
    pub name: String,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub settings: BTreeMap<String, Value>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub mappings: BTreeMap<String, Value>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub aliases: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct MigrationTranslationReport {
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub indices: BTreeMap<String, SteelsearchIndexDefinition>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub legacy_templates: BTreeMap<String, Value>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub index_templates: BTreeMap<String, Value>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub component_templates: BTreeMap<String, Value>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub data_streams: BTreeMap<String, Value>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub vector_fields: BTreeMap<String, Vec<VectorFieldMigration>>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub unsupported_features: Vec<UnsupportedFeature>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct VectorFieldMigration {
    pub index: String,
    pub field: String,
    pub dimension: u32,
    pub data_type: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub engine: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub space_type: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub method_name: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub method_engine: Option<String>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub method_parameters: BTreeMap<String, Value>,
    pub requires_vector_reindex: bool,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub notes: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct UnsupportedFeature {
    pub index: String,
    pub path: String,
    pub feature: String,
    pub reason: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MigrationValidationInput {
    pub index: String,
    pub source_document_count: u64,
    pub target_document_count: u64,
    pub source_id_checksum: u64,
    pub target_id_checksum: u64,
    pub source_source_checksum: u64,
    pub target_source_checksum: u64,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub sample_queries: Vec<SampleQueryValidation>,
    #[serde(default, skip_serializing_if = "BTreeSet::is_empty")]
    pub expected_aliases: BTreeSet<String>,
    #[serde(default, skip_serializing_if = "BTreeSet::is_empty")]
    pub actual_aliases: BTreeSet<String>,
    #[serde(default, skip_serializing_if = "BTreeSet::is_empty")]
    pub expected_data_streams: BTreeSet<String>,
    #[serde(default, skip_serializing_if = "BTreeSet::is_empty")]
    pub actual_data_streams: BTreeSet<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct VectorDocumentValidationIssue {
    pub index: String,
    pub field: String,
    pub id: String,
    pub reason: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SampleQueryValidation {
    pub name: String,
    pub source_total_hits: u64,
    pub target_total_hits: u64,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub source_top_ids: Vec<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub target_top_ids: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CutoverReadinessReport {
    pub ready: bool,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub index_reports: Vec<IndexValidationReport>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub blockers: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexValidationReport {
    pub index: String,
    pub ready: bool,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub checks: Vec<ValidationCheck>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ValidationCheck {
    pub name: String,
    pub passed: bool,
    pub expected: String,
    pub actual: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum MigrationError {
    InvalidJson(String),
    InvalidShape(String),
    InvalidExportRequest(String),
    InvalidImportRequest(String),
}

impl fmt::Display for MigrationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidJson(reason) => write!(formatter, "invalid migration JSON: {reason}"),
            Self::InvalidShape(reason) => {
                write!(formatter, "invalid migration source shape: {reason}")
            }
            Self::InvalidExportRequest(reason) => {
                write!(formatter, "invalid document export request: {reason}")
            }
            Self::InvalidImportRequest(reason) => {
                write!(formatter, "invalid document import request: {reason}")
            }
        }
    }
}

impl std::error::Error for MigrationError {}

impl MigrationSourceInventory {
    pub fn from_slice(bytes: &[u8]) -> Result<Self, MigrationError> {
        let value: Value = serde_json::from_slice(bytes)
            .map_err(|error| MigrationError::InvalidJson(error.to_string()))?;
        Self::from_value(&value)
    }

    pub fn from_value(value: &Value) -> Result<Self, MigrationError> {
        let object = value.as_object().ok_or_else(|| {
            MigrationError::InvalidShape("migration source must be a JSON object".to_string())
        })?;

        let mut inventory = MigrationSourceInventory::default();
        if let Some(indices) = object.get("indices").and_then(Value::as_object) {
            inventory.indices.extend(read_indices(indices)?);
        }
        if let Some(metadata_indices) = object
            .get("metadata")
            .and_then(|metadata| metadata.get("indices"))
            .and_then(Value::as_object)
        {
            merge_index_metadata(&mut inventory.indices, metadata_indices)?;
        }

        inventory.legacy_templates = read_named_object(object.get("templates"));
        inventory.index_templates = read_index_templates(object.get("index_templates"));
        inventory.component_templates = read_component_templates(object.get("component_templates"));
        inventory.ingest_pipelines = read_named_object(
            object
                .get("ingest_pipelines")
                .or_else(|| object.get("pipelines")),
        );
        inventory.data_streams = read_data_streams(object.get("data_streams"));

        Ok(inventory)
    }

    pub fn index_count(&self) -> usize {
        self.indices.len()
    }

    pub fn translate_to_steelsearch(&self) -> MigrationTranslationReport {
        let mut report = MigrationTranslationReport {
            legacy_templates: self.legacy_templates.clone(),
            index_templates: self.index_templates.clone(),
            component_templates: self.component_templates.clone(),
            data_streams: self.data_streams.clone(),
            ..MigrationTranslationReport::default()
        };
        for index in self.indices.values() {
            let (definition, vector_fields, mut unsupported) = translate_index(index);
            report.indices.insert(index.name.clone(), definition);
            if !vector_fields.is_empty() {
                report
                    .vector_fields
                    .insert(index.name.clone(), vector_fields);
            }
            report.unsupported_features.append(&mut unsupported);
        }
        report
    }
}

impl DocumentExportPlan {
    pub fn build(request: DocumentExportRequest) -> Result<Self, MigrationError> {
        validate_export_request(&request)?;
        let slices = (0..request.slices)
            .map(|slice_id| DocumentExportSlice {
                slice_id,
                max_slices: request.slices,
                resume: request
                    .checkpoint
                    .as_ref()
                    .filter(|checkpoint| checkpoint.slice_id == slice_id)
                    .cloned(),
            })
            .collect();

        Ok(Self {
            index: request.index,
            mode: request.mode,
            page_size: request.page_size,
            slices,
            retry: request.retry,
            throttle: request.throttle,
            backoff: request.backoff,
        })
    }

    pub fn checkpoint_for_slice(
        &self,
        slice_id: u32,
        cursor: ExportCursor,
        exported_documents: u64,
    ) -> Result<ExportCheckpoint, MigrationError> {
        if !self.slices.iter().any(|slice| slice.slice_id == slice_id) {
            return Err(MigrationError::InvalidExportRequest(format!(
                "slice [{slice_id}] is not part of export plan"
            )));
        }
        let mut checkpoint = ExportCheckpoint {
            index: self.index.clone(),
            slice_id,
            scroll_id: None,
            pit_id: None,
            search_after: Vec::new(),
            exported_documents,
        };
        match cursor {
            ExportCursor::Scroll { scroll_id } => checkpoint.scroll_id = Some(scroll_id),
            ExportCursor::PitSearchAfter {
                pit_id,
                search_after,
            } => {
                checkpoint.pit_id = Some(pit_id);
                checkpoint.search_after = search_after;
            }
        }
        Ok(checkpoint)
    }
}

impl BulkImportPlan {
    pub fn build(
        request: BulkImportRequest,
        documents: Vec<BulkImportDocument>,
    ) -> Result<Self, MigrationError> {
        validate_import_request(&request)?;
        let documents: Vec<_> = documents
            .into_iter()
            .filter(|document| {
                request.checkpoint.as_ref().map_or(true, |checkpoint| {
                    document.exported_sequence > checkpoint.last_exported_sequence
                })
            })
            .map(|mut document| {
                document.target_index = request.target_index.clone();
                document
            })
            .collect();

        let batches = documents
            .chunks(request.batch_size)
            .enumerate()
            .map(|(batch_id, chunk)| BulkImportBatch {
                batch_id: batch_id as u64,
                operations: chunk
                    .iter()
                    .map(|document| BulkOperation {
                        op_type: BulkOperationType::Index,
                        source_index: document.source_index.clone(),
                        target_index: document.target_index.clone(),
                        id: document.id.clone(),
                        routing: document.routing.clone(),
                        source: document.source.clone(),
                        exported_sequence: document.exported_sequence,
                    })
                    .collect(),
            })
            .collect();

        Ok(Self {
            target_index: request.target_index,
            batch_size: request.batch_size,
            max_concurrency: request.max_concurrency,
            max_in_flight_batches: request.max_in_flight_batches,
            batches,
            resume_from: request.checkpoint,
        })
    }

    pub fn checkpoint_after_batch(
        &self,
        batch: &BulkImportBatch,
        failed_documents: u64,
    ) -> BulkImportCheckpoint {
        let last_exported_sequence = batch
            .operations
            .iter()
            .map(|operation| operation.exported_sequence)
            .max()
            .unwrap_or_else(|| {
                self.resume_from
                    .as_ref()
                    .map_or(0, |checkpoint| checkpoint.last_exported_sequence)
            });
        let previously_imported = self
            .resume_from
            .as_ref()
            .map_or(0, |checkpoint| checkpoint.imported_documents);
        let previously_failed = self
            .resume_from
            .as_ref()
            .map_or(0, |checkpoint| checkpoint.failed_documents);
        let successful_documents = (batch.operations.len() as u64).saturating_sub(failed_documents);
        BulkImportCheckpoint {
            target_index: self.target_index.clone(),
            last_exported_sequence,
            imported_documents: previously_imported + successful_documents,
            failed_documents: previously_failed + failed_documents,
        }
    }

    pub fn capture_failure(
        &self,
        operation: &BulkOperation,
        status: u16,
        error_type: impl Into<String>,
        reason: impl Into<String>,
    ) -> BulkItemFailure {
        BulkItemFailure {
            target_index: operation.target_index.clone(),
            id: operation.id.clone(),
            status,
            error_type: error_type.into(),
            reason: reason.into(),
            document: Some(BulkImportDocument {
                source_index: operation.source_index.clone(),
                target_index: operation.target_index.clone(),
                id: operation.id.clone(),
                routing: operation.routing.clone(),
                source: operation.source.clone(),
                exported_sequence: operation.exported_sequence,
            }),
        }
    }
}

impl BulkItemFailure {
    pub fn dead_letter_record(&self) -> Option<DeadLetterRecord> {
        self.document.as_ref().map(|document| DeadLetterRecord {
            target_index: self.target_index.clone(),
            id: self.id.clone(),
            reason: format!("{}: {}", self.error_type, self.reason),
            source: document.source.clone(),
        })
    }
}

pub fn build_cutover_readiness_report(
    inputs: Vec<MigrationValidationInput>,
) -> CutoverReadinessReport {
    let mut index_reports = Vec::new();
    let mut blockers = Vec::new();

    for input in inputs {
        let mut checks = Vec::new();
        push_check(
            &mut checks,
            format!("{}.document_count", input.index),
            input.source_document_count,
            input.target_document_count,
        );
        push_check(
            &mut checks,
            format!("{}.id_checksum", input.index),
            input.source_id_checksum,
            input.target_id_checksum,
        );
        push_check(
            &mut checks,
            format!("{}.source_checksum", input.index),
            input.source_source_checksum,
            input.target_source_checksum,
        );
        push_check(
            &mut checks,
            format!("{}.aliases", input.index),
            format_set(&input.expected_aliases),
            format_set(&input.actual_aliases),
        );
        push_check(
            &mut checks,
            format!("{}.data_streams", input.index),
            format_set(&input.expected_data_streams),
            format_set(&input.actual_data_streams),
        );
        for query in input.sample_queries {
            push_check(
                &mut checks,
                format!("{}.query.{}.total_hits", input.index, query.name),
                query.source_total_hits,
                query.target_total_hits,
            );
            push_check(
                &mut checks,
                format!("{}.query.{}.top_ids", input.index, query.name),
                query.source_top_ids.join(","),
                query.target_top_ids.join(","),
            );
        }

        let ready = checks.iter().all(|check| check.passed);
        blockers.extend(
            checks
                .iter()
                .filter(|check| !check.passed)
                .map(|check| check.name.clone()),
        );
        index_reports.push(IndexValidationReport {
            index: input.index,
            ready,
            checks,
        });
    }

    CutoverReadinessReport {
        ready: blockers.is_empty(),
        index_reports,
        blockers,
    }
}

pub fn checksum_document_ids(documents: &[BulkImportDocument]) -> u64 {
    let mut ids: Vec<_> = documents
        .iter()
        .map(|document| document.id.as_str())
        .collect();
    ids.sort_unstable();

    let mut checksum = FNV_OFFSET_BASIS;
    for id in ids {
        checksum = checksum_bytes_with_seed(checksum, id.as_bytes());
        checksum = checksum_bytes_with_seed(checksum, &[0]);
    }
    checksum
}

pub fn checksum_document_sources(documents: &[BulkImportDocument]) -> u64 {
    let mut documents: Vec<_> = documents.iter().collect();
    documents.sort_by(|left, right| left.id.cmp(&right.id));

    let mut checksum = FNV_OFFSET_BASIS;
    for document in documents {
        let source_bytes = serde_json::to_vec(&document.source).unwrap_or_default();
        checksum = checksum_bytes_with_seed(checksum, document.id.as_bytes());
        checksum = checksum_bytes_with_seed(checksum, &[0]);
        checksum = checksum_bytes_with_seed(checksum, &source_bytes);
        checksum = checksum_bytes_with_seed(checksum, &[0]);
    }
    checksum
}

pub fn validate_vector_documents(
    index: impl Into<String>,
    field: impl Into<String>,
    expected_dimension: u32,
    documents: &[BulkImportDocument],
) -> Vec<VectorDocumentValidationIssue> {
    let index = index.into();
    let field = field.into();
    let mut issues = Vec::new();
    for document in documents {
        let Some(value) = nested_field_value(&document.source, &field) else {
            issues.push(VectorDocumentValidationIssue {
                index: index.clone(),
                field: field.clone(),
                id: document.id.clone(),
                reason: "vector field is missing".to_string(),
            });
            continue;
        };
        let Some(values) = value.as_array() else {
            issues.push(VectorDocumentValidationIssue {
                index: index.clone(),
                field: field.clone(),
                id: document.id.clone(),
                reason: "vector field must be an array".to_string(),
            });
            continue;
        };
        if values.len() != expected_dimension as usize {
            issues.push(VectorDocumentValidationIssue {
                index: index.clone(),
                field: field.clone(),
                id: document.id.clone(),
                reason: format!(
                    "vector dimension [{}] does not match expected [{}]",
                    values.len(),
                    expected_dimension
                ),
            });
            continue;
        }
        if values.iter().any(|value| !value.is_number()) {
            issues.push(VectorDocumentValidationIssue {
                index: index.clone(),
                field: field.clone(),
                id: document.id.clone(),
                reason: "vector field must contain only numeric values".to_string(),
            });
        }
    }
    issues
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub enum ExportCursor {
    Scroll {
        scroll_id: String,
    },
    PitSearchAfter {
        pit_id: String,
        search_after: Vec<Value>,
    },
}

const FNV_OFFSET_BASIS: u64 = 0xcbf29ce484222325;
const FNV_PRIME: u64 = 0x100000001b3;

fn push_check<T>(checks: &mut Vec<ValidationCheck>, name: String, expected: T, actual: T)
where
    T: fmt::Display + PartialEq,
{
    let passed = expected == actual;
    checks.push(ValidationCheck {
        name,
        passed,
        expected: expected.to_string(),
        actual: actual.to_string(),
    });
}

fn format_set(values: &BTreeSet<String>) -> String {
    values.iter().cloned().collect::<Vec<_>>().join(",")
}

fn checksum_bytes_with_seed(mut checksum: u64, bytes: &[u8]) -> u64 {
    for byte in bytes {
        checksum ^= u64::from(*byte);
        checksum = checksum.wrapping_mul(FNV_PRIME);
    }
    checksum
}

fn nested_field_value<'a>(source: &'a Value, field: &str) -> Option<&'a Value> {
    let mut current = source;
    for segment in field.split('.') {
        current = current.get(segment)?;
    }
    Some(current)
}

fn validate_export_request(request: &DocumentExportRequest) -> Result<(), MigrationError> {
    if request.index.trim().is_empty() {
        return Err(MigrationError::InvalidExportRequest(
            "index must not be empty".to_string(),
        ));
    }
    if request.page_size == 0 {
        return Err(MigrationError::InvalidExportRequest(
            "page_size must be greater than zero".to_string(),
        ));
    }
    if request.slices == 0 {
        return Err(MigrationError::InvalidExportRequest(
            "slices must be greater than zero".to_string(),
        ));
    }
    if request.retry.max_attempts == 0 {
        return Err(MigrationError::InvalidExportRequest(
            "retry max_attempts must be greater than zero".to_string(),
        ));
    }
    if request.throttle.requests_per_second == 0 {
        return Err(MigrationError::InvalidExportRequest(
            "throttle requests_per_second must be greater than zero".to_string(),
        ));
    }
    if request.backoff.initial_millis == 0
        || request.backoff.max_millis < request.backoff.initial_millis
    {
        return Err(MigrationError::InvalidExportRequest(
            "backoff must have positive initial_millis and max >= initial".to_string(),
        ));
    }
    if let Some(checkpoint) = request.checkpoint.as_ref() {
        if checkpoint.index != request.index {
            return Err(MigrationError::InvalidExportRequest(
                "checkpoint index must match export index".to_string(),
            ));
        }
        if checkpoint.slice_id >= request.slices {
            return Err(MigrationError::InvalidExportRequest(
                "checkpoint slice_id must be within export slices".to_string(),
            ));
        }
        match (
            &request.mode,
            checkpoint.scroll_id.as_ref(),
            checkpoint.pit_id.as_ref(),
        ) {
            (DocumentExportMode::Scroll { .. }, Some(_), None) => {}
            (DocumentExportMode::PitSearchAfter { .. }, None, Some(_)) => {}
            _ => {
                return Err(MigrationError::InvalidExportRequest(
                    "checkpoint cursor must match export mode".to_string(),
                ));
            }
        }
    }
    Ok(())
}

fn validate_import_request(request: &BulkImportRequest) -> Result<(), MigrationError> {
    if request.target_index.trim().is_empty() {
        return Err(MigrationError::InvalidImportRequest(
            "target_index must not be empty".to_string(),
        ));
    }
    if request.batch_size == 0 {
        return Err(MigrationError::InvalidImportRequest(
            "batch_size must be greater than zero".to_string(),
        ));
    }
    if request.max_concurrency == 0 {
        return Err(MigrationError::InvalidImportRequest(
            "max_concurrency must be greater than zero".to_string(),
        ));
    }
    if request.max_in_flight_batches < request.max_concurrency {
        return Err(MigrationError::InvalidImportRequest(
            "max_in_flight_batches must be at least max_concurrency".to_string(),
        ));
    }
    if let Some(checkpoint) = request.checkpoint.as_ref() {
        if checkpoint.target_index != request.target_index {
            return Err(MigrationError::InvalidImportRequest(
                "checkpoint target_index must match import target_index".to_string(),
            ));
        }
    }
    Ok(())
}

fn translate_index(
    index: &SourceIndexMetadata,
) -> (
    SteelsearchIndexDefinition,
    Vec<VectorFieldMigration>,
    Vec<UnsupportedFeature>,
) {
    let mut unsupported = Vec::new();
    let settings = translate_settings(index, &mut unsupported);
    let mappings = translate_mappings(index, &mut unsupported);
    let vector_fields = collect_vector_migrations(index, &mut unsupported);

    (
        SteelsearchIndexDefinition {
            name: index.name.clone(),
            settings,
            mappings,
            aliases: index.aliases.clone(),
        },
        vector_fields,
        unsupported,
    )
}

fn translate_settings(
    index: &SourceIndexMetadata,
    unsupported: &mut Vec<UnsupportedFeature>,
) -> BTreeMap<String, Value> {
    let mut translated = BTreeMap::new();
    let Some(settings_index) = index.settings.get("index").and_then(Value::as_object) else {
        return translated;
    };

    for (key, value) in settings_index {
        match key.as_str() {
            "number_of_shards" | "number_of_replicas" | "refresh_interval" => {
                translated.insert(format!("index.{key}"), value.clone());
            }
            "uuid" | "provided_name" | "creation_date" | "version" => {}
            unsupported_key => unsupported.push(UnsupportedFeature {
                index: index.name.clone(),
                path: format!("settings.index.{unsupported_key}"),
                feature: unsupported_key.to_string(),
                reason: "setting is not translated to Steelsearch yet".to_string(),
            }),
        }
    }
    translated
}

fn translate_mappings(
    index: &SourceIndexMetadata,
    unsupported: &mut Vec<UnsupportedFeature>,
) -> BTreeMap<String, Value> {
    let mut translated = BTreeMap::new();
    if let Some(dynamic) = index.mappings.get("dynamic") {
        translated.insert("dynamic".to_string(), dynamic.clone());
    }
    if let Some(properties) = index.mappings.get("properties").and_then(Value::as_object) {
        let mut translated_properties = serde_json::Map::new();
        for (field, mapping) in properties {
            if let Some(translated_mapping) =
                translate_field_mapping(index, field, mapping, unsupported)
            {
                translated_properties.insert(field.clone(), translated_mapping);
            }
        }
        translated.insert(
            "properties".to_string(),
            Value::Object(translated_properties),
        );
    }
    translated
}

fn translate_field_mapping(
    index: &SourceIndexMetadata,
    field: &str,
    mapping: &Value,
    unsupported: &mut Vec<UnsupportedFeature>,
) -> Option<Value> {
    let object = mapping.as_object()?;
    let field_type = object
        .get("type")
        .and_then(Value::as_str)
        .unwrap_or("object");

    if !is_supported_field_type(field_type) {
        unsupported.push(UnsupportedFeature {
            index: index.name.clone(),
            path: format!("mappings.properties.{field}"),
            feature: field_type.to_string(),
            reason: "field type is not supported by the current Steelsearch migration target"
                .to_string(),
        });
        return None;
    }

    let mut translated = serde_json::Map::new();
    translated.insert("type".to_string(), Value::String(field_type.to_string()));
    if field_type == "knn_vector" {
        for option in [
            "dimension",
            "data_type",
            "method",
            "engine",
            "space_type",
            "mode",
            "compression_level",
        ] {
            if let Some(value) = object.get(option) {
                translated.insert(option.to_string(), value.clone());
            }
        }
        return Some(Value::Object(translated));
    }
    for option in ["analyzer", "search_analyzer", "format", "ignore_above"] {
        if let Some(value) = object.get(option) {
            translated.insert(option.to_string(), value.clone());
        }
    }
    if let Some(properties) = object.get("properties").and_then(Value::as_object) {
        let mut nested_properties = serde_json::Map::new();
        for (nested_field, nested_mapping) in properties {
            let nested_path = format!("{field}.{nested_field}");
            if let Some(translated_nested) =
                translate_field_mapping(index, &nested_path, nested_mapping, unsupported)
            {
                nested_properties.insert(nested_field.clone(), translated_nested);
            }
        }
        translated.insert("properties".to_string(), Value::Object(nested_properties));
    }

    for key in object.keys() {
        if !matches!(
            key.as_str(),
            "type" | "analyzer" | "search_analyzer" | "format" | "ignore_above" | "properties"
        ) {
            unsupported.push(UnsupportedFeature {
                index: index.name.clone(),
                path: format!("mappings.properties.{field}.{key}"),
                feature: key.clone(),
                reason: "mapping option is preserved only when explicitly supported".to_string(),
            });
        }
    }

    Some(Value::Object(translated))
}

fn is_supported_field_type(field_type: &str) -> bool {
    matches!(
        field_type,
        "text"
            | "keyword"
            | "integer"
            | "long"
            | "short"
            | "byte"
            | "float"
            | "double"
            | "boolean"
            | "date"
            | "object"
            | "knn_vector"
    )
}

fn collect_vector_migrations(
    index: &SourceIndexMetadata,
    unsupported: &mut Vec<UnsupportedFeature>,
) -> Vec<VectorFieldMigration> {
    let mut migrations = Vec::new();
    if let Some(properties) = index.mappings.get("properties").and_then(Value::as_object) {
        collect_vector_migrations_from_properties(
            index,
            "",
            properties,
            unsupported,
            &mut migrations,
        );
    }
    migrations
}

fn collect_vector_migrations_from_properties(
    index: &SourceIndexMetadata,
    prefix: &str,
    properties: &serde_json::Map<String, Value>,
    unsupported: &mut Vec<UnsupportedFeature>,
    migrations: &mut Vec<VectorFieldMigration>,
) {
    for (field, mapping) in properties {
        let path = if prefix.is_empty() {
            field.clone()
        } else {
            format!("{prefix}.{field}")
        };
        let Some(object) = mapping.as_object() else {
            continue;
        };
        if object.get("type").and_then(Value::as_str) == Some("knn_vector") {
            if let Some(migration) = vector_field_migration(index, &path, object, unsupported) {
                migrations.push(migration);
            }
        }
        if let Some(nested) = object.get("properties").and_then(Value::as_object) {
            collect_vector_migrations_from_properties(
                index,
                &path,
                nested,
                unsupported,
                migrations,
            );
        }
    }
}

fn vector_field_migration(
    index: &SourceIndexMetadata,
    field: &str,
    mapping: &serde_json::Map<String, Value>,
    unsupported: &mut Vec<UnsupportedFeature>,
) -> Option<VectorFieldMigration> {
    let dimension = mapping
        .get("dimension")
        .and_then(Value::as_u64)
        .or_else(|| {
            mapping
                .get("dimension")
                .and_then(Value::as_str)
                .and_then(|value| value.parse::<u64>().ok())
        });
    let Some(dimension) = dimension else {
        unsupported.push(UnsupportedFeature {
            index: index.name.clone(),
            path: format!("mappings.properties.{field}.dimension"),
            feature: "knn_vector.dimension".to_string(),
            reason: "knn_vector migration requires an explicit dimension".to_string(),
        });
        return None;
    };

    let data_type = mapping
        .get("data_type")
        .and_then(Value::as_str)
        .unwrap_or("float")
        .to_string();
    let engine = mapping
        .get("engine")
        .and_then(Value::as_str)
        .map(str::to_string);
    let space_type = mapping
        .get("space_type")
        .and_then(Value::as_str)
        .map(str::to_string);
    let method = mapping.get("method").and_then(Value::as_object);
    let method_name = method
        .and_then(|method| method.get("name"))
        .and_then(Value::as_str)
        .map(str::to_string);
    let method_engine = method
        .and_then(|method| method.get("engine"))
        .and_then(Value::as_str)
        .map(str::to_string);
    let method_parameters = method
        .and_then(|method| method.get("parameters"))
        .and_then(Value::as_object)
        .map(|parameters| {
            parameters
                .iter()
                .map(|(key, value)| (key.clone(), value.clone()))
                .collect()
        })
        .unwrap_or_default();

    let source_engine = method_engine.as_deref().or(engine.as_deref());
    let requires_vector_reindex = source_engine != Some("steelsearch");
    let mut notes = Vec::new();
    if let Some(engine) = source_engine {
        notes.push(format!(
            "source vector engine [{engine}] will be rebuilt into Steelsearch-native vector segments"
        ));
    } else {
        notes.push(
            "source vector engine is unspecified; rebuild vector index during import".to_string(),
        );
    }
    if data_type != "float" {
        notes.push(format!(
            "source vector data_type [{data_type}] requires compatibility validation"
        ));
    }

    Some(VectorFieldMigration {
        index: index.name.clone(),
        field: field.to_string(),
        dimension: dimension as u32,
        data_type,
        engine,
        space_type,
        method_name,
        method_engine,
        method_parameters,
        requires_vector_reindex,
        notes,
    })
}

fn read_indices(
    indices: &serde_json::Map<String, Value>,
) -> Result<BTreeMap<String, SourceIndexMetadata>, MigrationError> {
    let mut output = BTreeMap::new();
    for (name, value) in indices {
        let object = value.as_object().ok_or_else(|| {
            MigrationError::InvalidShape(format!("index [{name}] metadata must be an object"))
        })?;
        output.insert(
            name.clone(),
            SourceIndexMetadata {
                name: name.clone(),
                settings: object_to_map(object.get("settings")),
                mappings: object_to_map(object.get("mappings")),
                aliases: object_to_map(object.get("aliases")),
                state: object
                    .get("state")
                    .and_then(Value::as_str)
                    .map(str::to_string),
                uuid: object
                    .get("settings")
                    .and_then(|settings| settings.get("index"))
                    .and_then(|index| index.get("uuid"))
                    .and_then(Value::as_str)
                    .map(str::to_string),
                raw_metadata: object_to_map(Some(value)),
            },
        );
    }
    Ok(output)
}

fn merge_index_metadata(
    indices: &mut BTreeMap<String, SourceIndexMetadata>,
    metadata_indices: &serde_json::Map<String, Value>,
) -> Result<(), MigrationError> {
    for (name, value) in metadata_indices {
        let object = value.as_object().ok_or_else(|| {
            MigrationError::InvalidShape(format!("metadata index [{name}] must be an object"))
        })?;
        let entry = indices
            .entry(name.clone())
            .or_insert_with(|| SourceIndexMetadata {
                name: name.clone(),
                ..SourceIndexMetadata::default()
            });
        if entry.settings.is_empty() {
            entry.settings = object_to_map(object.get("settings"));
        }
        if entry.mappings.is_empty() {
            entry.mappings = object_to_map(object.get("mappings"));
        }
        if entry.aliases.is_empty() {
            entry.aliases = object_to_map(object.get("aliases"));
        }
        entry.state = entry.state.clone().or_else(|| {
            object
                .get("state")
                .and_then(Value::as_str)
                .map(str::to_string)
        });
        entry.uuid = entry.uuid.clone().or_else(|| {
            object
                .get("settings")
                .and_then(|settings| settings.get("index"))
                .and_then(|index| index.get("uuid"))
                .and_then(Value::as_str)
                .map(str::to_string)
        });
        entry.raw_metadata = object_to_map(Some(value));
    }
    Ok(())
}

fn read_named_object(value: Option<&Value>) -> BTreeMap<String, Value> {
    value
        .and_then(Value::as_object)
        .map(|object| {
            object
                .iter()
                .map(|(key, value)| (key.clone(), value.clone()))
                .collect()
        })
        .unwrap_or_default()
}

fn read_index_templates(value: Option<&Value>) -> BTreeMap<String, Value> {
    if let Some(array) = value.and_then(Value::as_array) {
        return array
            .iter()
            .filter_map(|entry| {
                let name = entry.get("name")?.as_str()?.to_string();
                Some((name, entry.clone()))
            })
            .collect();
    }
    read_named_object(value)
}

fn read_component_templates(value: Option<&Value>) -> BTreeMap<String, Value> {
    if let Some(array) = value.and_then(Value::as_array) {
        return array
            .iter()
            .filter_map(|entry| {
                let name = entry.get("name")?.as_str()?.to_string();
                Some((name, entry.clone()))
            })
            .collect();
    }
    read_named_object(value)
}

fn read_data_streams(value: Option<&Value>) -> BTreeMap<String, Value> {
    if let Some(array) = value.and_then(Value::as_array) {
        return array
            .iter()
            .filter_map(|entry| {
                let name = entry.get("name")?.as_str()?.to_string();
                Some((name, entry.clone()))
            })
            .collect();
    }
    read_named_object(value)
}

fn object_to_map(value: Option<&Value>) -> BTreeMap<String, Value> {
    value
        .and_then(Value::as_object)
        .map(|object| {
            object
                .iter()
                .map(|(key, value)| (key.clone(), value.clone()))
                .collect()
        })
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn reads_index_mappings_settings_aliases_and_metadata() {
        let source = json!({
            "indices": {
                "logs-000001": {
                    "settings": {
                        "index": {
                            "uuid": "uuid-1",
                            "number_of_shards": "1"
                        }
                    },
                    "mappings": {
                        "properties": {
                            "message": { "type": "text" }
                        }
                    },
                    "aliases": {
                        "logs": {}
                    },
                    "state": "open"
                }
            }
        });

        let inventory = MigrationSourceInventory::from_value(&source).unwrap();
        let index = inventory.indices.get("logs-000001").unwrap();
        assert_eq!(inventory.index_count(), 1);
        assert_eq!(index.uuid.as_deref(), Some("uuid-1"));
        assert_eq!(index.state.as_deref(), Some("open"));
        assert!(index.mappings.contains_key("properties"));
        assert!(index.aliases.contains_key("logs"));
    }

    #[test]
    fn reads_templates_pipelines_and_data_streams() {
        let source = json!({
            "templates": {
                "legacy-template": { "index_patterns": ["legacy-*"] }
            },
            "index_templates": [
                { "name": "logs-template", "index_template": { "index_patterns": ["logs-*"] } }
            ],
            "component_templates": [
                { "name": "settings-component", "component_template": { "template": {} } }
            ],
            "ingest_pipelines": {
                "pipeline-1": { "processors": [] }
            },
            "data_streams": [
                { "name": "logs", "timestamp_field": { "name": "@timestamp" } }
            ]
        });

        let inventory = MigrationSourceInventory::from_value(&source).unwrap();
        assert!(inventory.legacy_templates.contains_key("legacy-template"));
        assert!(inventory.index_templates.contains_key("logs-template"));
        assert!(inventory
            .component_templates
            .contains_key("settings-component"));
        assert!(inventory.ingest_pipelines.contains_key("pipeline-1"));
        assert!(inventory.data_streams.contains_key("logs"));
    }

    #[test]
    fn merges_cluster_metadata_indices_when_index_api_shape_is_absent() {
        let source = json!({
            "metadata": {
                "indices": {
                    "metrics-000001": {
                        "settings": {
                            "index": {
                                "uuid": "uuid-2"
                            }
                        },
                        "mappings": {
                            "properties": {
                                "value": { "type": "double" }
                            }
                        },
                        "aliases": {
                            "metrics": {}
                        }
                    }
                }
            }
        });

        let inventory = MigrationSourceInventory::from_value(&source).unwrap();
        let index = inventory.indices.get("metrics-000001").unwrap();
        assert_eq!(index.uuid.as_deref(), Some("uuid-2"));
        assert!(index.mappings.contains_key("properties"));
        assert!(index.aliases.contains_key("metrics"));
    }

    #[test]
    fn builds_scroll_export_plan_with_slices_retry_throttle_and_checkpoint() {
        let checkpoint = ExportCheckpoint {
            index: "logs-000001".to_string(),
            slice_id: 1,
            scroll_id: Some("scroll-1".to_string()),
            pit_id: None,
            search_after: Vec::new(),
            exported_documents: 500,
        };
        let plan = DocumentExportPlan::build(DocumentExportRequest {
            index: "logs-000001".to_string(),
            mode: DocumentExportMode::Scroll {
                keep_alive: "5m".to_string(),
            },
            page_size: 1_000,
            slices: 3,
            retry: RetryPolicy { max_attempts: 5 },
            throttle: ThrottlePolicy {
                requests_per_second: 20,
            },
            backoff: BackoffPolicy {
                initial_millis: 100,
                max_millis: 5_000,
            },
            checkpoint: Some(checkpoint.clone()),
        })
        .unwrap();

        assert_eq!(plan.slices.len(), 3);
        assert_eq!(plan.slices[1].resume.as_ref(), Some(&checkpoint));
        assert!(plan.slices[0].resume.is_none());
        assert!(plan.slices[2].resume.is_none());
        assert_eq!(plan.retry.max_attempts, 5);
        assert_eq!(plan.throttle.requests_per_second, 20);

        let next_checkpoint = plan
            .checkpoint_for_slice(
                1,
                ExportCursor::Scroll {
                    scroll_id: "scroll-2".to_string(),
                },
                checkpoint.exported_documents + 250,
            )
            .unwrap();
        assert_eq!(next_checkpoint.index, "logs-000001");
        assert_eq!(next_checkpoint.slice_id, 1);
        assert_eq!(next_checkpoint.scroll_id.as_deref(), Some("scroll-2"));
        assert!(next_checkpoint.pit_id.is_none());
        assert_eq!(next_checkpoint.exported_documents, 750);
    }

    #[test]
    fn builds_pit_search_after_checkpoint_for_resumable_export() {
        let resume = ExportCheckpoint {
            index: "metrics-000001".to_string(),
            slice_id: 1,
            scroll_id: None,
            pit_id: Some("pit-resume".to_string()),
            search_after: vec![json!(41), json!("doc-41")],
            exported_documents: 41,
        };
        let plan = DocumentExportPlan::build(DocumentExportRequest {
            index: "metrics-000001".to_string(),
            mode: DocumentExportMode::PitSearchAfter {
                pit_keep_alive: "2m".to_string(),
            },
            page_size: 500,
            slices: 2,
            retry: RetryPolicy { max_attempts: 3 },
            throttle: ThrottlePolicy {
                requests_per_second: 10,
            },
            backoff: BackoffPolicy {
                initial_millis: 200,
                max_millis: 2_000,
            },
            checkpoint: Some(resume.clone()),
        })
        .unwrap();

        assert_eq!(plan.slices.len(), 2);
        assert!(plan.slices[0].resume.is_none());
        assert_eq!(plan.slices[1].resume.as_ref(), Some(&resume));

        let checkpoint = plan
            .checkpoint_for_slice(
                1,
                ExportCursor::PitSearchAfter {
                    pit_id: "pit-1".to_string(),
                    search_after: vec![json!(42), json!("doc-42")],
                },
                42,
            )
            .unwrap();
        assert_eq!(checkpoint.pit_id.as_deref(), Some("pit-1"));
        assert_eq!(checkpoint.search_after, vec![json!(42), json!("doc-42")]);
        assert_eq!(checkpoint.exported_documents, 42);
    }

    #[test]
    fn rejects_mismatched_export_checkpoint_mode() {
        let error = DocumentExportPlan::build(DocumentExportRequest {
            index: "logs".to_string(),
            mode: DocumentExportMode::Scroll {
                keep_alive: "5m".to_string(),
            },
            page_size: 100,
            slices: 1,
            retry: RetryPolicy { max_attempts: 1 },
            throttle: ThrottlePolicy {
                requests_per_second: 1,
            },
            backoff: BackoffPolicy {
                initial_millis: 1,
                max_millis: 1,
            },
            checkpoint: Some(ExportCheckpoint {
                index: "logs".to_string(),
                slice_id: 0,
                scroll_id: None,
                pit_id: Some("pit-1".to_string()),
                search_after: Vec::new(),
                exported_documents: 0,
            }),
        })
        .unwrap_err();

        assert!(matches!(error, MigrationError::InvalidExportRequest(_)));
    }

    #[test]
    fn builds_bulk_import_batches_with_backpressure_and_resume() {
        let documents = sample_documents(5);
        let plan = BulkImportPlan::build(
            BulkImportRequest {
                target_index: "logs-steel".to_string(),
                batch_size: 2,
                max_concurrency: 2,
                max_in_flight_batches: 4,
                checkpoint: Some(BulkImportCheckpoint {
                    target_index: "logs-steel".to_string(),
                    last_exported_sequence: 1,
                    imported_documents: 2,
                    failed_documents: 0,
                }),
            },
            documents,
        )
        .unwrap();

        assert_eq!(plan.batches.len(), 2);
        assert_eq!(plan.batches[0].operations.len(), 2);
        assert_eq!(plan.batches[0].operations[0].id, "doc-2");
        assert_eq!(plan.max_concurrency, 2);
        assert_eq!(plan.max_in_flight_batches, 4);

        let checkpoint = plan.checkpoint_after_batch(&plan.batches[0], 1);
        assert_eq!(checkpoint.last_exported_sequence, 3);
        assert_eq!(checkpoint.imported_documents, 3);
        assert_eq!(checkpoint.failed_documents, 1);
    }

    #[test]
    fn bulk_import_resume_is_retry_safe_without_duplicates_or_gaps() {
        let documents = sample_documents(6);
        let initial_plan = BulkImportPlan::build(
            BulkImportRequest {
                target_index: "logs-steel".to_string(),
                batch_size: 2,
                max_concurrency: 1,
                max_in_flight_batches: 1,
                checkpoint: None,
            },
            documents.clone(),
        )
        .unwrap();
        let first_checkpoint = initial_plan.checkpoint_after_batch(&initial_plan.batches[0], 0);

        assert_eq!(first_checkpoint.last_exported_sequence, 1);
        assert_eq!(first_checkpoint.imported_documents, 2);
        assert_eq!(first_checkpoint.failed_documents, 0);

        let resumed_plan = BulkImportPlan::build(
            BulkImportRequest {
                target_index: "logs-steel".to_string(),
                batch_size: 2,
                max_concurrency: 1,
                max_in_flight_batches: 1,
                checkpoint: Some(first_checkpoint.clone()),
            },
            documents.clone(),
        )
        .unwrap();
        let resumed_ids = resumed_plan
            .batches
            .iter()
            .flat_map(|batch| batch.operations.iter().map(|document| document.id.as_str()))
            .collect::<Vec<_>>();

        assert_eq!(resumed_ids, vec!["doc-2", "doc-3", "doc-4", "doc-5"]);
        assert!(!resumed_ids
            .iter()
            .any(|id| *id == "doc-0" || *id == "doc-1"));

        let second_checkpoint = resumed_plan.checkpoint_after_batch(&resumed_plan.batches[0], 1);
        assert_eq!(second_checkpoint.last_exported_sequence, 3);
        assert_eq!(second_checkpoint.imported_documents, 3);
        assert_eq!(second_checkpoint.failed_documents, 1);

        let final_plan = BulkImportPlan::build(
            BulkImportRequest {
                target_index: "logs-steel".to_string(),
                batch_size: 10,
                max_concurrency: 1,
                max_in_flight_batches: 1,
                checkpoint: Some(second_checkpoint),
            },
            documents,
        )
        .unwrap();
        let final_ids = final_plan
            .batches
            .iter()
            .flat_map(|batch| batch.operations.iter().map(|document| document.id.as_str()))
            .collect::<Vec<_>>();

        assert_eq!(final_ids, vec!["doc-4", "doc-5"]);

        let all_imported_ids = initial_plan.batches[0]
            .operations
            .iter()
            .chain(resumed_plan.batches[0].operations.iter())
            .chain(final_plan.batches[0].operations.iter())
            .map(|operation| operation.id.clone())
            .collect::<Vec<_>>();
        let unique_imported_ids = all_imported_ids.iter().cloned().collect::<BTreeSet<_>>();
        let source_ids = sample_documents(6)
            .into_iter()
            .map(|document| document.id)
            .collect::<BTreeSet<_>>();
        assert_eq!(all_imported_ids.len(), unique_imported_ids.len());
        assert_eq!(unique_imported_ids, source_ids);
    }

    #[test]
    fn captures_bulk_failure_as_dead_letter_record() {
        let document = sample_documents(1).remove(0);
        let failure = BulkItemFailure {
            target_index: "logs-steel".to_string(),
            id: document.id.clone(),
            status: 400,
            error_type: "mapper_parsing_exception".to_string(),
            reason: "failed to parse field".to_string(),
            document: Some(document.clone()),
        };

        let dead_letter = failure.dead_letter_record().unwrap();
        assert_eq!(dead_letter.id, document.id);
        assert_eq!(dead_letter.target_index, "logs-steel");
        assert!(dead_letter.reason.contains("mapper_parsing_exception"));
        assert_eq!(dead_letter.source["message"], json!("doc 0"));
    }

    #[test]
    fn import_plan_captures_failures_as_dead_letters_and_checkpoint_counts() {
        let documents = sample_documents(4);
        let plan = BulkImportPlan::build(
            BulkImportRequest {
                target_index: "logs-steel".to_string(),
                batch_size: 4,
                max_concurrency: 1,
                max_in_flight_batches: 1,
                checkpoint: None,
            },
            documents.clone(),
        )
        .unwrap();
        let batch = &plan.batches[0];

        let failures = vec![
            plan.capture_failure(
                &batch.operations[1],
                400,
                "mapper_parsing_exception",
                "failed to parse field [bytes]",
            ),
            plan.capture_failure(
                &batch.operations[3],
                409,
                "version_conflict_engine_exception",
                "version conflict while importing",
            ),
        ];

        let dead_letters = failures
            .iter()
            .filter_map(BulkItemFailure::dead_letter_record)
            .collect::<Vec<_>>();

        assert_eq!(dead_letters.len(), 2);
        assert_eq!(dead_letters[0].target_index, "logs-steel");
        assert_eq!(dead_letters[0].id, "doc-1");
        assert!(dead_letters[0].reason.contains("mapper_parsing_exception"));
        assert_eq!(dead_letters[0].source["message"], json!("doc 1"));
        assert_eq!(
            failures[0].document.as_ref().unwrap().source_index,
            documents[1].source_index
        );
        assert_eq!(
            failures[0].document.as_ref().unwrap().exported_sequence,
            documents[1].exported_sequence
        );
        assert_eq!(dead_letters[1].id, "doc-3");
        assert!(dead_letters[1]
            .reason
            .contains("version_conflict_engine_exception"));
        assert_eq!(dead_letters[1].source["message"], json!("doc 3"));

        let checkpoint = plan.checkpoint_after_batch(batch, failures.len() as u64);
        assert_eq!(checkpoint.target_index, "logs-steel");
        assert_eq!(checkpoint.last_exported_sequence, 3);
        assert_eq!(checkpoint.imported_documents, 2);
        assert_eq!(checkpoint.failed_documents, 2);
    }

    #[test]
    fn rejects_import_backpressure_below_concurrency() {
        let error = BulkImportPlan::build(
            BulkImportRequest {
                target_index: "logs-steel".to_string(),
                batch_size: 100,
                max_concurrency: 4,
                max_in_flight_batches: 2,
                checkpoint: None,
            },
            Vec::new(),
        )
        .unwrap_err();

        assert!(matches!(error, MigrationError::InvalidImportRequest(_)));
    }

    #[test]
    fn translates_supported_mappings_and_settings() {
        let inventory = MigrationSourceInventory::from_value(&json!({
            "indices": {
                "logs": {
                    "settings": {
                        "index": {
                            "uuid": "uuid-1",
                            "number_of_shards": "3",
                            "number_of_replicas": "1",
                            "refresh_interval": "1s"
                        }
                    },
                    "mappings": {
                        "dynamic": "strict",
                        "properties": {
                            "message": { "type": "text", "analyzer": "standard" },
                            "status": { "type": "keyword", "ignore_above": 256 },
                            "count": { "type": "long" }
                        }
                    },
                    "aliases": { "logs-read": {} }
                }
            }
        }))
        .unwrap();

        let report = inventory.translate_to_steelsearch();
        let definition = report.indices.get("logs").unwrap();
        assert_eq!(definition.settings["index.number_of_shards"], json!("3"));
        assert_eq!(definition.settings["index.refresh_interval"], json!("1s"));
        assert_eq!(definition.mappings["dynamic"], json!("strict"));
        assert_eq!(
            definition.mappings["properties"]["message"]["type"],
            json!("text")
        );
        assert!(definition.aliases.contains_key("logs-read"));
        assert!(report.unsupported_features.is_empty());
    }

    #[test]
    fn translates_alias_templates_data_streams_and_validates_vector_documents() {
        let inventory = MigrationSourceInventory::from_value(&json!({
            "component_templates": [
                {
                    "name": "logs-settings",
                    "component_template": {
                        "template": {
                            "settings": {
                                "index": {
                                    "number_of_shards": "1"
                                }
                            }
                        }
                    }
                }
            ],
            "index_templates": [
                {
                    "name": "logs-template",
                    "index_template": {
                        "index_patterns": ["logs-*"],
                        "composed_of": ["logs-settings"],
                        "data_stream": {}
                    }
                }
            ],
            "data_streams": [
                {
                    "name": "logs",
                    "timestamp_field": {
                        "name": "@timestamp"
                    },
                    "indices": [
                        { "index_name": ".ds-logs-000001" }
                    ]
                }
            ],
            "indices": {
                ".ds-logs-000001": {
                    "settings": {
                        "index": {
                            "number_of_shards": "1",
                            "number_of_replicas": "1"
                        }
                    },
                    "mappings": {
                        "properties": {
                            "@timestamp": { "type": "date" },
                            "embedding": {
                                "type": "knn_vector",
                                "dimension": 3,
                                "data_type": "float",
                                "method": {
                                    "name": "hnsw",
                                    "engine": "faiss"
                                }
                            }
                        }
                    },
                    "aliases": {
                        "logs-read": {},
                        "logs-write": { "is_write_index": true }
                    }
                }
            }
        }))
        .unwrap();

        let report = inventory.translate_to_steelsearch();
        let definition = report.indices.get(".ds-logs-000001").unwrap();
        assert!(definition.aliases.contains_key("logs-read"));
        assert!(definition.aliases.contains_key("logs-write"));
        assert!(report.index_templates.contains_key("logs-template"));
        assert!(report.component_templates.contains_key("logs-settings"));
        assert!(report.data_streams.contains_key("logs"));

        let vector = &report.vector_fields[".ds-logs-000001"][0];
        assert_eq!(vector.field, "embedding");
        assert_eq!(vector.dimension, 3);
        assert!(vector.requires_vector_reindex);

        let documents = vec![
            BulkImportDocument {
                source_index: ".ds-logs-000001".to_string(),
                target_index: ".ds-logs-000001".to_string(),
                id: "doc-good".to_string(),
                routing: None,
                source: json!({
                    "@timestamp": "2026-04-22T00:00:00Z",
                    "embedding": [0.1, 0.2, 0.3]
                }),
                exported_sequence: 0,
            },
            BulkImportDocument {
                source_index: ".ds-logs-000001".to_string(),
                target_index: ".ds-logs-000001".to_string(),
                id: "doc-bad-dimension".to_string(),
                routing: None,
                source: json!({
                    "@timestamp": "2026-04-22T00:00:01Z",
                    "embedding": [0.1, 0.2]
                }),
                exported_sequence: 1,
            },
            BulkImportDocument {
                source_index: ".ds-logs-000001".to_string(),
                target_index: ".ds-logs-000001".to_string(),
                id: "doc-bad-value".to_string(),
                routing: None,
                source: json!({
                    "@timestamp": "2026-04-22T00:00:02Z",
                    "embedding": [0.1, "not-a-number", 0.3]
                }),
                exported_sequence: 2,
            },
        ];

        let issues = validate_vector_documents(".ds-logs-000001", "embedding", 3, &documents);
        let issue_ids = issues
            .iter()
            .map(|issue| issue.id.as_str())
            .collect::<Vec<_>>();
        assert_eq!(issue_ids, vec!["doc-bad-dimension", "doc-bad-value"]);
        assert!(issues[0].reason.contains("does not match expected"));
        assert!(issues[1].reason.contains("numeric"));
    }

    #[test]
    fn reports_unsupported_mapping_types_and_settings() {
        let inventory = MigrationSourceInventory::from_value(&json!({
            "indices": {
                "products": {
                    "settings": {
                        "index": {
                            "number_of_shards": "1",
                            "sort.field": "category"
                        }
                    },
                    "mappings": {
                        "properties": {
                            "shape": { "type": "geo_shape" },
                            "title": { "type": "text", "term_vector": "with_positions_offsets" }
                        }
                    }
                }
            }
        }))
        .unwrap();

        let report = inventory.translate_to_steelsearch();
        let unsupported: Vec<_> = report
            .unsupported_features
            .iter()
            .map(|feature| feature.path.as_str())
            .collect();
        assert!(unsupported.contains(&"settings.index.sort.field"));
        assert!(unsupported.contains(&"mappings.properties.shape"));
        assert!(unsupported.contains(&"mappings.properties.title.term_vector"));
        assert!(report.indices["products"].mappings["properties"]
            .get("shape")
            .is_none());
    }

    #[test]
    fn migrates_knn_vector_mapping_with_reindex_notes() {
        let inventory = MigrationSourceInventory::from_value(&json!({
            "indices": {
                "semantic": {
                    "mappings": {
                        "properties": {
                            "embedding": {
                                "type": "knn_vector",
                                "dimension": 384,
                                "data_type": "float",
                                "space_type": "l2",
                                "method": {
                                    "name": "hnsw",
                                    "engine": "faiss",
                                    "parameters": {
                                        "ef_construction": 128,
                                        "m": 16
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }))
        .unwrap();

        let report = inventory.translate_to_steelsearch();
        let vector_fields = report.vector_fields.get("semantic").unwrap();
        assert_eq!(vector_fields.len(), 1);
        assert_eq!(vector_fields[0].field, "embedding");
        assert_eq!(vector_fields[0].dimension, 384);
        assert_eq!(vector_fields[0].method_name.as_deref(), Some("hnsw"));
        assert_eq!(vector_fields[0].method_engine.as_deref(), Some("faiss"));
        assert!(vector_fields[0].requires_vector_reindex);
        assert_eq!(
            report.indices["semantic"].mappings["properties"]["embedding"]["dimension"],
            json!(384)
        );
    }

    #[test]
    fn reports_knn_vector_without_dimension() {
        let inventory = MigrationSourceInventory::from_value(&json!({
            "indices": {
                "semantic": {
                    "mappings": {
                        "properties": {
                            "embedding": {
                                "type": "knn_vector",
                                "method": { "name": "hnsw" }
                            }
                        }
                    }
                }
            }
        }))
        .unwrap();

        let report = inventory.translate_to_steelsearch();
        assert!(report.vector_fields.get("semantic").is_none());
        assert!(report
            .unsupported_features
            .iter()
            .any(|feature| feature.path == "mappings.properties.embedding.dimension"));
    }

    #[test]
    fn builds_ready_cutover_report_when_all_validation_checks_match() {
        let documents = sample_documents(3);
        let id_checksum = checksum_document_ids(&documents);
        let source_checksum = checksum_document_sources(&documents);

        let report = build_cutover_readiness_report(vec![MigrationValidationInput {
            index: "logs".to_string(),
            source_document_count: documents.len() as u64,
            target_document_count: documents.len() as u64,
            source_id_checksum: id_checksum,
            target_id_checksum: id_checksum,
            source_source_checksum: source_checksum,
            target_source_checksum: source_checksum,
            sample_queries: vec![SampleQueryValidation {
                name: "recent-errors".to_string(),
                source_total_hits: 2,
                target_total_hits: 2,
                source_top_ids: vec!["doc-0".to_string(), "doc-1".to_string()],
                target_top_ids: vec!["doc-0".to_string(), "doc-1".to_string()],
            }],
            expected_aliases: set(["logs-read"]),
            actual_aliases: set(["logs-read"]),
            expected_data_streams: set(["logs"]),
            actual_data_streams: set(["logs"]),
        }]);

        assert!(report.ready);
        assert!(report.blockers.is_empty());
        assert!(report.index_reports[0]
            .checks
            .iter()
            .all(|check| check.passed));
    }

    #[test]
    fn cutover_report_blocks_on_count_checksums_alias_data_stream_and_query_mismatches() {
        let source_documents = sample_documents(2);
        let mut target_documents = sample_documents(2);
        target_documents[0].id = "doc-mismatch".to_string();
        target_documents[1].source = json!({ "message": "changed" });

        let report = build_cutover_readiness_report(vec![MigrationValidationInput {
            index: "logs".to_string(),
            source_document_count: 2,
            target_document_count: 1,
            source_id_checksum: checksum_document_ids(&source_documents),
            target_id_checksum: checksum_document_ids(&target_documents),
            source_source_checksum: checksum_document_sources(&source_documents),
            target_source_checksum: checksum_document_sources(&target_documents),
            sample_queries: vec![SampleQueryValidation {
                name: "recent-errors".to_string(),
                source_total_hits: 2,
                target_total_hits: 1,
                source_top_ids: vec!["doc-0".to_string(), "doc-1".to_string()],
                target_top_ids: vec!["doc-1".to_string(), "doc-0".to_string()],
            }],
            expected_aliases: set(["logs-read", "logs-write"]),
            actual_aliases: set(["logs-read"]),
            expected_data_streams: set(["logs"]),
            actual_data_streams: set(["logs-reindexed"]),
        }]);

        assert!(!report.ready);
        assert!(report.blockers.contains(&"logs.document_count".to_string()));
        assert!(report.blockers.contains(&"logs.id_checksum".to_string()));
        assert!(report
            .blockers
            .contains(&"logs.source_checksum".to_string()));
        assert!(report.blockers.contains(&"logs.aliases".to_string()));
        assert!(report.blockers.contains(&"logs.data_streams".to_string()));
        assert!(report
            .blockers
            .contains(&"logs.query.recent-errors.total_hits".to_string()));
        assert!(report
            .blockers
            .contains(&"logs.query.recent-errors.top_ids".to_string()));
    }

    #[test]
    fn document_checksums_are_order_independent_for_ids_and_sources() {
        let documents = sample_documents(4);
        let mut reversed = documents.clone();
        reversed.reverse();

        assert_eq!(
            checksum_document_ids(&documents),
            checksum_document_ids(&reversed)
        );
        assert_eq!(
            checksum_document_sources(&documents),
            checksum_document_sources(&reversed)
        );
    }

    fn sample_documents(count: u64) -> Vec<BulkImportDocument> {
        (0..count)
            .map(|sequence| BulkImportDocument {
                source_index: "logs".to_string(),
                target_index: "logs-steel".to_string(),
                id: format!("doc-{sequence}"),
                routing: None,
                source: json!({ "message": format!("doc {sequence}") }),
                exported_sequence: sequence,
            })
            .collect()
    }

    fn set<const N: usize>(values: [&str; N]) -> BTreeSet<String> {
        values.into_iter().map(str::to_string).collect()
    }
}
