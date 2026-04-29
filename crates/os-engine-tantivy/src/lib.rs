//! Tantivy-backed engine placeholder.

use os_engine::{
    load_shard_manifest, persist_shard_manifest, ConditionalDeleteDocumentRequest,
    ConditionalIndexDocumentRequest, ConditionalUpdateDocumentRequest, CreateIndexRequest,
    CreateIndexResponse, DeleteDocumentRequest, DocumentMetadata, EngineError, EngineResult,
    GetDocumentRequest, GetDocumentResponse, IndexDocumentRequest, IndexDocumentResponse,
    IndexEngine, RefreshPolicy, RefreshRequest, RefreshResponse, ReplayDocumentRequest,
    SearchCacheIndexTelemetrySnapshot, SearchCacheTelemetryDetails,
    SearchCacheTelemetrySnapshot, SearchFetchSubphase,
    SearchFetchSubphaseResult, SearchHit,
    SearchMemoryReservation, SearchMemoryUsageCounters, SearchPhase, SearchPhaseResult,
    SearchRequest, SearchResponse,
    ShardManifest, SortOrder, SortSpec, TranslogLocation, UpdateDocumentRequest,
    VectorSegmentMetadata, VersionType, WriteCondition, WriteCoordinationMetadata, WriteResult,
};
use os_plugin_knn::{
    parse_knn_vector_mapping, KnnVectorDataType, KnnVectorMapping, KNN_VECTOR_FIELD_TYPE,
    KNN_VECTOR_FORMAT,
};
use os_query_dsl::{
    parse_aggregation_map, parse_query, Aggregation, AggregationMap, BoolQuery, KnnQuery,
    Query, RangeBounds,
};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::path::Path;
use std::sync::{Arc, Mutex};

const SHARD_OPERATIONS_FILE_NAME: &str = "steelsearch-operations.jsonl";
const MAX_KNN_CACHE_ENTRIES_PER_FIELD: usize = 16;
const MAX_KNN_CACHE_BYTES_PER_FIELD: usize = 256 * 1024;

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct TantivyIndexSchema {
    pub number_of_shards: u32,
    pub number_of_replicas: u32,
    pub dynamic: bool,
    pub fields: Vec<TantivyFieldMapping>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct TantivyFieldMapping {
    pub name: String,
    pub field_type: TantivyFieldType,
    pub indexed: bool,
    pub stored: bool,
    pub fast: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub knn_vector: Option<KnnVectorMapping>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TantivyFieldType {
    Text,
    Keyword,
    I64,
    F64,
    Bool,
    Date,
    GeoPoint,
    KnnVector,
}

pub fn map_opensearch_index_to_tantivy_schema(
    request: &CreateIndexRequest,
) -> EngineResult<TantivyIndexSchema> {
    Ok(TantivyIndexSchema {
        number_of_shards: read_u32_setting(&request.settings, "number_of_shards", 1)?,
        number_of_replicas: read_u32_setting(&request.settings, "number_of_replicas", 1)?,
        dynamic: read_dynamic_mapping(&request.mappings)?,
        fields: read_field_mappings(&request.mappings)?,
    })
}

#[derive(Debug, Default)]
pub struct TantivyEngine {
    store: Arc<Mutex<EngineStore>>,
}

#[derive(Debug, Default)]
struct EngineStore {
    indices: BTreeMap<String, StoredIndex>,
}

#[derive(Debug)]
struct StoredIndex {
    index_name: String,
    index_uuid: String,
    allocation_id: String,
    schema: TantivyIndexSchema,
    schema_hash: u64,
    documents: BTreeMap<String, StoredDocument>,
    next_seq_no: i64,
    refreshed_seq_no: i64,
    primary_term: u64,
    committed_generation: u64,
    translog_generation: u64,
    collector_telemetry: SearchCollectorTelemetry,
    runtime_cache: SearchRuntimeCache,
}

#[derive(Clone, Debug)]
struct StoredDocument {
    metadata: DocumentMetadata,
    coordination: WriteCoordinationMetadata,
    source: Value,
    vector_fields: BTreeMap<String, StoredVectorField>,
}

#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
struct StoredVectorField {
    values: Vec<VectorValue>,
}

#[derive(Clone, Debug, Default)]
struct SearchCollectorTelemetry {
    knn_collector_bytes_by_field: BTreeMap<String, usize>,
}

#[derive(Clone, Debug, Default)]
struct SearchRuntimeCache {
    knn_search_by_field: BTreeMap<String, CachedKnnSearchFieldCache>,
    vector_graph_by_field: CachedResidentFieldCache,
    fast_fields_by_name: CachedResidentFieldCache,
    request_result_resets: u64,
    request_result_invalidated_entries: u64,
    request_result_refresh_invalidations: u64,
    request_result_stale_invalidations: u64,
    next_access_tick: u64,
}

#[derive(Clone, Debug, Default)]
struct CachedKnnSearchFieldCache {
    entries: BTreeMap<String, CachedKnnSearchEntry>,
    resident_bytes: usize,
    hits: u64,
    misses: u64,
    evictions: u64,
    capacity_evictions: u64,
    resets: u64,
    invalidated_entries: u64,
    refresh_invalidations: u64,
    stale_invalidations: u64,
}

#[derive(Clone, Debug)]
struct CachedKnnSearchEntry {
    refreshed_seq_no: i64,
    query: KnnQuery,
    hits: Vec<SearchHit>,
    resident_bytes: usize,
    last_access_tick: u64,
}

#[derive(Clone, Debug)]
struct CachedResidentFieldCacheEntry {
    resident_bytes: usize,
    last_access_tick: u64,
}

#[derive(Clone, Debug, Default)]
struct CachedResidentFieldTelemetry {
    hits: u64,
    misses: u64,
    evictions: u64,
    capacity_evictions: u64,
    resets: u64,
    invalidated_entries: u64,
    refresh_invalidations: u64,
    stale_invalidations: u64,
}

#[derive(Clone, Debug, Default)]
struct CachedResidentFieldCache {
    entries: BTreeMap<String, CachedResidentFieldCacheEntry>,
    telemetry_by_field: BTreeMap<String, CachedResidentFieldTelemetry>,
    resident_bytes: usize,
    hits: u64,
    misses: u64,
    evictions: u64,
    capacity_evictions: u64,
    resets: u64,
    invalidated_entries: u64,
    refresh_invalidations: u64,
    stale_invalidations: u64,
}

impl SearchRuntimeCache {
    fn next_access_tick(&mut self) -> u64 {
        self.next_access_tick = self.next_access_tick.saturating_add(1);
        self.next_access_tick
    }

    fn clear_knn_results(&mut self) {
        self.request_result_resets = self.request_result_resets.saturating_add(1);
        let request_result_invalidated_entries = self
            .knn_search_by_field
            .values()
            .map(|field_cache| field_cache.entries.len() as u64)
            .sum::<u64>();
        for field_cache in self.knn_search_by_field.values_mut() {
            let invalidated_entries = field_cache.entries.len() as u64;
            field_cache.resets = field_cache.resets.saturating_add(1);
            field_cache.invalidated_entries = field_cache
                .invalidated_entries
                .saturating_add(invalidated_entries);
            field_cache.refresh_invalidations = field_cache
                .refresh_invalidations
                .saturating_add(invalidated_entries);
        }
        self.request_result_invalidated_entries = self
            .request_result_invalidated_entries
            .saturating_add(request_result_invalidated_entries);
        self.request_result_refresh_invalidations = self
            .request_result_refresh_invalidations
            .saturating_add(request_result_invalidated_entries);
        self.vector_graph_by_field.resets = self.vector_graph_by_field.resets.saturating_add(1);
        let vector_graph_invalidated_entries = self.vector_graph_by_field.entries.len() as u64;
        self.vector_graph_by_field.invalidated_entries = self
            .vector_graph_by_field
            .invalidated_entries
            .saturating_add(vector_graph_invalidated_entries);
        self.vector_graph_by_field.refresh_invalidations = self
            .vector_graph_by_field
            .refresh_invalidations
            .saturating_add(vector_graph_invalidated_entries);
        for field in self.vector_graph_by_field.entries.keys() {
            let telemetry = self
                .vector_graph_by_field
                .telemetry_by_field
                .entry(field.clone())
                .or_default();
            telemetry.resets = telemetry.resets.saturating_add(1);
            telemetry.invalidated_entries = telemetry.invalidated_entries.saturating_add(1);
            telemetry.refresh_invalidations = telemetry.refresh_invalidations.saturating_add(1);
        }
        self.fast_fields_by_name.resets = self.fast_fields_by_name.resets.saturating_add(1);
        let fast_field_invalidated_entries = self.fast_fields_by_name.entries.len() as u64;
        self.fast_fields_by_name.invalidated_entries = self
            .fast_fields_by_name
            .invalidated_entries
            .saturating_add(fast_field_invalidated_entries);
        self.fast_fields_by_name.refresh_invalidations = self
            .fast_fields_by_name
            .refresh_invalidations
            .saturating_add(fast_field_invalidated_entries);
        for field in self.fast_fields_by_name.entries.keys() {
            let telemetry = self
                .fast_fields_by_name
                .telemetry_by_field
                .entry(field.clone())
                .or_default();
            telemetry.resets = telemetry.resets.saturating_add(1);
            telemetry.invalidated_entries = telemetry.invalidated_entries.saturating_add(1);
            telemetry.refresh_invalidations = telemetry.refresh_invalidations.saturating_add(1);
        }
        for field_cache in self.knn_search_by_field.values_mut() {
            field_cache.entries.clear();
            field_cache.resident_bytes = 0;
        }
        self.vector_graph_by_field.entries.clear();
        self.vector_graph_by_field.resident_bytes = 0;
        self.fast_fields_by_name.entries.clear();
        self.fast_fields_by_name.resident_bytes = 0;
    }

    fn insert_knn_entry(
        &mut self,
        field: String,
        cache_key: String,
        entry: CachedKnnSearchEntry,
    ) {
        let field_cache = self.knn_search_by_field.entry(field.clone()).or_default();
        if let Some(previous) = field_cache.entries.remove(&cache_key) {
            field_cache.resident_bytes = field_cache
                .resident_bytes
                .saturating_sub(previous.resident_bytes);
        }
        field_cache.resident_bytes = field_cache
            .resident_bytes
            .saturating_add(entry.resident_bytes);
        field_cache.entries.insert(cache_key, entry);
        evict_knn_cache_entries(field_cache);
    }

    fn touch_vector_graph_cache(
        &mut self,
        field: String,
        resident_bytes: usize,
    ) {
        let access_tick = self.next_access_tick();
        touch_resident_field_cache(
            &mut self.vector_graph_by_field,
            field,
            CachedResidentFieldCacheEntry {
                resident_bytes,
                last_access_tick: access_tick,
            },
        );
    }

    fn touch_fast_field_cache(
        &mut self,
        field: String,
        resident_bytes: usize,
    ) {
        let access_tick = self.next_access_tick();
        touch_resident_field_cache(
            &mut self.fast_fields_by_name,
            field,
            CachedResidentFieldCacheEntry {
                resident_bytes,
                last_access_tick: access_tick,
            },
        );
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct VectorSearchHit {
    pub id: String,
    pub score: f32,
    pub source: Value,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct NativeHnswIndexSnapshot {
    pub field: String,
    pub dimension: usize,
    pub nodes: Vec<NativeHnswNodeSnapshot>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct NativeHnswNodeSnapshot {
    pub id: String,
    pub neighbors: Vec<String>,
}

type VectorValue = f32;

impl IndexEngine for TantivyEngine {
    fn create_index(&self, request: CreateIndexRequest) -> EngineResult<CreateIndexResponse> {
        let schema = map_opensearch_index_to_tantivy_schema(&request)?;
        let schema_hash = schema_hash(&request.index, &schema)?;
        let mut store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        if store.indices.contains_key(&request.index) {
            return Err(EngineError::IndexAlreadyExists {
                index: request.index,
            });
        }
        store.indices.insert(
            request.index.clone(),
            StoredIndex {
                index_name: request.index.clone(),
                index_uuid: format!("steelsearch-{schema_hash:016x}"),
                allocation_id: format!("alloc-{schema_hash:016x}-0"),
                schema,
                schema_hash,
                documents: BTreeMap::new(),
                next_seq_no: 0,
                refreshed_seq_no: -1,
                primary_term: 1,
                committed_generation: 0,
                translog_generation: 0,
                collector_telemetry: SearchCollectorTelemetry::default(),
                runtime_cache: SearchRuntimeCache::default(),
            },
        );
        Ok(CreateIndexResponse {
            index: request.index,
            acknowledged: true,
        })
    }

    fn index_document(&self, request: IndexDocumentRequest) -> EngineResult<IndexDocumentResponse> {
        let mut store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let Some(index) = store.indices.get_mut(&request.index) else {
            return Err(EngineError::IndexNotFound {
                index: request.index,
            });
        };

        index.ensure_dynamic_mappings(&request.source)?;
        let (metadata, coordination, result) =
            index.apply_primary_document(request.id, request.source);

        Ok(IndexDocumentResponse {
            index: request.index,
            metadata,
            coordination,
            result,
        })
    }

    fn index_document_with_refresh(
        &self,
        request: IndexDocumentRequest,
        refresh_policy: RefreshPolicy,
    ) -> EngineResult<IndexDocumentResponse> {
        let response = self.index_document(request)?;
        self.apply_write_refresh_policy(&response.index, refresh_policy)?;
        Ok(response)
    }

    fn index_document_with_control(
        &self,
        request: ConditionalIndexDocumentRequest,
    ) -> EngineResult<IndexDocumentResponse> {
        let mut store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let Some(index) = store.indices.get_mut(&request.request.index) else {
            return Err(EngineError::IndexNotFound {
                index: request.request.index,
            });
        };

        index.ensure_dynamic_mappings(&request.request.source)?;
        let version_override =
            validate_write_condition(index.documents.get(&request.request.id), &request.condition)?;
        let (metadata, coordination, result) = index.apply_primary_document_with_version(
            request.request.id,
            request.request.source,
            version_override,
        );

        Ok(IndexDocumentResponse {
            index: request.request.index,
            metadata,
            coordination,
            result,
        })
    }

    fn replay_document(
        &self,
        request: ReplayDocumentRequest,
    ) -> EngineResult<IndexDocumentResponse> {
        let mut store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let Some(index) = store.indices.get_mut(&request.index) else {
            return Err(EngineError::IndexNotFound {
                index: request.index,
            });
        };

        let metadata = request.metadata;
        let coordination = request.coordination;
        let result = index.apply_replayed_document(
            metadata.clone(),
            coordination.clone(),
            request.source,
        )?;

        Ok(IndexDocumentResponse {
            index: request.index,
            metadata,
            coordination,
            result,
        })
    }

    fn update_document(
        &self,
        request: UpdateDocumentRequest,
    ) -> EngineResult<IndexDocumentResponse> {
        let mut store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let Some(index) = store.indices.get_mut(&request.index) else {
            return Err(EngineError::IndexNotFound {
                index: request.index,
            });
        };

        index.ensure_dynamic_mappings(&request.doc)?;
        let (metadata, coordination, result) = index
            .apply_update_document(&request.id, request.doc, request.doc_as_upsert)
            .ok_or(EngineError::DocumentNotFound {
                index: request.index.clone(),
                id: request.id,
            })?;

        Ok(IndexDocumentResponse {
            index: request.index,
            metadata,
            coordination,
            result,
        })
    }

    fn update_document_with_refresh(
        &self,
        request: UpdateDocumentRequest,
        refresh_policy: RefreshPolicy,
    ) -> EngineResult<IndexDocumentResponse> {
        let response = self.update_document(request)?;
        self.apply_write_refresh_policy(&response.index, refresh_policy)?;
        Ok(response)
    }

    fn update_document_with_control(
        &self,
        request: ConditionalUpdateDocumentRequest,
    ) -> EngineResult<IndexDocumentResponse> {
        let mut store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let Some(index) = store.indices.get_mut(&request.request.index) else {
            return Err(EngineError::IndexNotFound {
                index: request.request.index,
            });
        };

        index.ensure_dynamic_mappings(&request.request.doc)?;
        let version_override =
            validate_write_condition(index.documents.get(&request.request.id), &request.condition)?;
        let (metadata, coordination, result) = index
            .apply_update_document_with_version(
                &request.request.id,
                request.request.doc,
                request.request.doc_as_upsert,
                version_override,
            )
            .ok_or(EngineError::DocumentNotFound {
                index: request.request.index.clone(),
                id: request.request.id,
            })?;

        Ok(IndexDocumentResponse {
            index: request.request.index,
            metadata,
            coordination,
            result,
        })
    }

    fn delete_document(
        &self,
        request: DeleteDocumentRequest,
    ) -> EngineResult<IndexDocumentResponse> {
        let mut store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let Some(index) = store.indices.get_mut(&request.index) else {
            return Err(EngineError::IndexNotFound {
                index: request.index,
            });
        };

        let (metadata, coordination) =
            index
                .apply_delete_document(&request.id)
                .ok_or(EngineError::DocumentNotFound {
                    index: request.index.clone(),
                    id: request.id,
                })?;

        Ok(IndexDocumentResponse {
            index: request.index,
            metadata,
            coordination,
            result: WriteResult::Deleted,
        })
    }

    fn delete_document_with_refresh(
        &self,
        request: DeleteDocumentRequest,
        refresh_policy: RefreshPolicy,
    ) -> EngineResult<IndexDocumentResponse> {
        let response = self.delete_document(request)?;
        self.apply_write_refresh_policy(&response.index, refresh_policy)?;
        Ok(response)
    }

    fn delete_document_with_control(
        &self,
        request: ConditionalDeleteDocumentRequest,
    ) -> EngineResult<IndexDocumentResponse> {
        let mut store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let Some(index) = store.indices.get_mut(&request.request.index) else {
            return Err(EngineError::IndexNotFound {
                index: request.request.index,
            });
        };

        let version_override =
            validate_write_condition(index.documents.get(&request.request.id), &request.condition)?;
        let (metadata, coordination) = index
            .apply_delete_document_with_version(&request.request.id, version_override)
            .ok_or(EngineError::DocumentNotFound {
                index: request.request.index.clone(),
                id: request.request.id,
            })?;

        Ok(IndexDocumentResponse {
            index: request.request.index,
            metadata,
            coordination,
            result: WriteResult::Deleted,
        })
    }

    fn get_document(
        &self,
        request: GetDocumentRequest,
    ) -> EngineResult<Option<GetDocumentResponse>> {
        let store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let Some(index) = store.indices.get(&request.index) else {
            return Err(EngineError::IndexNotFound {
                index: request.index,
            });
        };
        Ok(index
            .documents
            .get(&request.id)
            .map(|document| GetDocumentResponse {
                index: request.index,
                metadata: document.metadata.clone(),
                source: document.source.clone(),
                found: true,
            }))
    }

    fn refresh(&self, request: RefreshRequest) -> EngineResult<RefreshResponse> {
        let mut store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let index_names = if request.indices.is_empty() {
            store.indices.keys().cloned().collect::<Vec<_>>()
        } else {
            request.indices
        };

        for index_name in index_names {
            let Some(index) = store.indices.get_mut(&index_name) else {
                return Err(EngineError::IndexNotFound { index: index_name });
            };
            index.refreshed_seq_no = index.next_seq_no - 1;
            index.runtime_cache.clear_knn_results();
        }
        Ok(RefreshResponse { refreshed: true })
    }

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
        request: &SearchRequest,
    ) -> EngineResult<SearchMemoryUsageCounters> {
        let query = parse_query(&request.query)
            .map_err(|error| invalid_request(format!("failed to parse query: {error}")))?;
        let aggregation_map = parse_search_aggregation_map(&request.aggregations)?;
        let store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let index_names = if request.indices.is_empty() {
            store.indices.keys().cloned().collect::<Vec<_>>()
        } else {
            request.indices.clone()
        };

        let mut doc_values_bytes = 0usize;
        let mut vector_bytes = 0usize;
        let mut collector_bytes = 0usize;
        let mut request_result_cache_bytes = 0usize;
        let mut vector_graph_cache_bytes = 0usize;
        let mut fast_field_cache_bytes = 0usize;
        let mut cache_bytes = 0usize;
        for index_name in &index_names {
            let Some(index) = store.indices.get(index_name) else {
                return Err(EngineError::IndexNotFound {
                    index: index_name.clone(),
                });
            };
            doc_values_bytes = doc_values_bytes.saturating_add(
                estimate_doc_values_reservation_bytes(
                    index,
                    &request.sort,
                    &aggregation_map,
                ),
            );
            vector_bytes =
                vector_bytes.saturating_add(visible_vector_reservation_bytes(index, &query));
            collector_bytes =
                collector_bytes.saturating_add(collector_telemetry_bytes(index, &query));
            let request_result_cache = request_result_cache_bytes_for_query(index, &query);
            let vector_graph_cache = vector_graph_cache_bytes_for_query(index, &query);
            let fast_field_cache =
                fast_field_cache_bytes_for_request(index, &request.sort, &aggregation_map);
            request_result_cache_bytes =
                request_result_cache_bytes.saturating_add(request_result_cache);
            vector_graph_cache_bytes =
                vector_graph_cache_bytes.saturating_add(vector_graph_cache);
            fast_field_cache_bytes =
                fast_field_cache_bytes.saturating_add(fast_field_cache);
            cache_bytes = cache_bytes.saturating_add(cache_telemetry_bytes(
                index,
                &query,
                &request.sort,
                &aggregation_map,
            ));
        }

        Ok(SearchMemoryUsageCounters {
            doc_values_bytes,
            vector_bytes,
            collector_bytes,
            request_result_cache_bytes,
            vector_graph_cache_bytes,
            fast_field_cache_bytes,
            cache_bytes,
            transport_bytes: 0,
        })
    }

    fn search_cache_telemetry_snapshot(&self) -> EngineResult<SearchCacheTelemetrySnapshot> {
        let store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let mut snapshot = SearchCacheTelemetrySnapshot::default();
        for index in store.indices.values() {
            snapshot.request_result_cache_bytes = snapshot
                .request_result_cache_bytes
                .saturating_add(
                    index.runtime_cache
                        .knn_search_by_field
                        .values()
                        .map(|field_cache| field_cache.resident_bytes)
                        .sum::<usize>(),
                );
            snapshot.request_result_cache_entries = snapshot
                .request_result_cache_entries
                .saturating_add(
                    index.runtime_cache
                        .knn_search_by_field
                        .values()
                        .map(|field_cache| field_cache.entries.len())
                        .sum::<usize>(),
                );
            snapshot.request_result_cache_hits = snapshot
                .request_result_cache_hits
                .saturating_add(
                    index.runtime_cache
                        .knn_search_by_field
                        .values()
                        .map(|field_cache| field_cache.hits)
                        .sum::<u64>(),
                );
            snapshot.request_result_cache_misses = snapshot
                .request_result_cache_misses
                .saturating_add(
                    index.runtime_cache
                        .knn_search_by_field
                        .values()
                        .map(|field_cache| field_cache.misses)
                        .sum::<u64>(),
                );
            snapshot.request_result_cache_evictions = snapshot
                .request_result_cache_evictions
                .saturating_add(
                    index.runtime_cache
                        .knn_search_by_field
                        .values()
                        .map(|field_cache| field_cache.evictions)
                        .sum::<u64>(),
                );
            snapshot.request_result_cache_capacity_evictions = snapshot
                .request_result_cache_capacity_evictions
                .saturating_add(
                    index.runtime_cache
                        .knn_search_by_field
                        .values()
                        .map(|field_cache| field_cache.capacity_evictions)
                        .sum::<u64>(),
                );
            snapshot.request_result_cache_resets = snapshot
                .request_result_cache_resets
                .saturating_add(index.runtime_cache.request_result_resets);
            snapshot.request_result_cache_invalidated_entries = snapshot
                .request_result_cache_invalidated_entries
                .saturating_add(index.runtime_cache.request_result_invalidated_entries);
            snapshot.request_result_cache_refresh_invalidations = snapshot
                .request_result_cache_refresh_invalidations
                .saturating_add(index.runtime_cache.request_result_refresh_invalidations);
            snapshot.request_result_cache_stale_invalidations = snapshot
                .request_result_cache_stale_invalidations
                .saturating_add(index.runtime_cache.request_result_stale_invalidations);
            snapshot.vector_graph_cache_bytes = snapshot
                .vector_graph_cache_bytes
                .saturating_add(index.runtime_cache.vector_graph_by_field.resident_bytes);
            snapshot.vector_graph_cache_entries = snapshot
                .vector_graph_cache_entries
                .saturating_add(index.runtime_cache.vector_graph_by_field.entries.len());
            snapshot.vector_graph_cache_hits = snapshot
                .vector_graph_cache_hits
                .saturating_add(index.runtime_cache.vector_graph_by_field.hits);
            snapshot.vector_graph_cache_misses = snapshot
                .vector_graph_cache_misses
                .saturating_add(index.runtime_cache.vector_graph_by_field.misses);
            snapshot.vector_graph_cache_evictions = snapshot
                .vector_graph_cache_evictions
                .saturating_add(index.runtime_cache.vector_graph_by_field.evictions);
            snapshot.vector_graph_cache_capacity_evictions = snapshot
                .vector_graph_cache_capacity_evictions
                .saturating_add(index.runtime_cache.vector_graph_by_field.capacity_evictions);
            snapshot.vector_graph_cache_resets = snapshot
                .vector_graph_cache_resets
                .saturating_add(index.runtime_cache.vector_graph_by_field.resets);
            snapshot.vector_graph_cache_invalidated_entries = snapshot
                .vector_graph_cache_invalidated_entries
                .saturating_add(index.runtime_cache.vector_graph_by_field.invalidated_entries);
            snapshot.vector_graph_cache_refresh_invalidations = snapshot
                .vector_graph_cache_refresh_invalidations
                .saturating_add(index.runtime_cache.vector_graph_by_field.refresh_invalidations);
            snapshot.vector_graph_cache_stale_invalidations = snapshot
                .vector_graph_cache_stale_invalidations
                .saturating_add(index.runtime_cache.vector_graph_by_field.stale_invalidations);
            snapshot.fast_field_cache_bytes = snapshot
                .fast_field_cache_bytes
                .saturating_add(index.runtime_cache.fast_fields_by_name.resident_bytes);
            snapshot.fast_field_cache_entries = snapshot
                .fast_field_cache_entries
                .saturating_add(index.runtime_cache.fast_fields_by_name.entries.len());
            snapshot.fast_field_cache_hits = snapshot
                .fast_field_cache_hits
                .saturating_add(index.runtime_cache.fast_fields_by_name.hits);
            snapshot.fast_field_cache_misses = snapshot
                .fast_field_cache_misses
                .saturating_add(index.runtime_cache.fast_fields_by_name.misses);
            snapshot.fast_field_cache_evictions = snapshot
                .fast_field_cache_evictions
                .saturating_add(index.runtime_cache.fast_fields_by_name.evictions);
            snapshot.fast_field_cache_capacity_evictions = snapshot
                .fast_field_cache_capacity_evictions
                .saturating_add(index.runtime_cache.fast_fields_by_name.capacity_evictions);
            snapshot.fast_field_cache_resets = snapshot
                .fast_field_cache_resets
                .saturating_add(index.runtime_cache.fast_fields_by_name.resets);
            snapshot.fast_field_cache_invalidated_entries = snapshot
                .fast_field_cache_invalidated_entries
                .saturating_add(index.runtime_cache.fast_fields_by_name.invalidated_entries);
            snapshot.fast_field_cache_refresh_invalidations = snapshot
                .fast_field_cache_refresh_invalidations
                .saturating_add(index.runtime_cache.fast_fields_by_name.refresh_invalidations);
            snapshot.fast_field_cache_stale_invalidations = snapshot
                .fast_field_cache_stale_invalidations
                .saturating_add(index.runtime_cache.fast_fields_by_name.stale_invalidations);
        }
        Ok(snapshot)
    }

    fn search_cache_telemetry_details(&self) -> EngineResult<SearchCacheTelemetryDetails> {
        let store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let mut details = SearchCacheTelemetryDetails::default();
        for index in store.indices.values() {
            let mut index_snapshot = SearchCacheIndexTelemetrySnapshot::default();
            let current_tick = index.runtime_cache.next_access_tick;
            index_snapshot.summary.request_result_cache_bytes = index
                .runtime_cache
                .knn_search_by_field
                .values()
                .map(|field_cache| field_cache.resident_bytes)
                .sum();
            index_snapshot.summary.request_result_cache_entries = index
                .runtime_cache
                .knn_search_by_field
                .values()
                .map(|field_cache| field_cache.entries.len())
                .sum();
            index_snapshot.summary.request_result_cache_hits = index
                .runtime_cache
                .knn_search_by_field
                .values()
                .map(|field_cache| field_cache.hits)
                .sum();
            index_snapshot.summary.request_result_cache_misses = index
                .runtime_cache
                .knn_search_by_field
                .values()
                .map(|field_cache| field_cache.misses)
                .sum();
            index_snapshot.summary.request_result_cache_evictions = index
                .runtime_cache
                .knn_search_by_field
                .values()
                .map(|field_cache| field_cache.evictions)
                .sum();
            index_snapshot.summary.request_result_cache_capacity_evictions = index
                .runtime_cache
                .knn_search_by_field
                .values()
                .map(|field_cache| field_cache.capacity_evictions)
                .sum();
            index_snapshot.summary.request_result_cache_resets =
                index.runtime_cache.request_result_resets;
            index_snapshot.summary.request_result_cache_invalidated_entries =
                index.runtime_cache.request_result_invalidated_entries;
            index_snapshot.summary.request_result_cache_refresh_invalidations =
                index.runtime_cache.request_result_refresh_invalidations;
            index_snapshot.summary.request_result_cache_stale_invalidations =
                index.runtime_cache.request_result_stale_invalidations;
            (
                index_snapshot.request_result_cache_oldest_entry_age_ticks,
                index_snapshot.request_result_cache_newest_entry_age_ticks,
            ) = resident_entry_age_bounds(
                current_tick,
                index
                    .runtime_cache
                    .knn_search_by_field
                    .values()
                    .flat_map(|field_cache| field_cache.entries.values().map(|entry| entry.last_access_tick)),
            );
            for (field, field_cache) in &index.runtime_cache.knn_search_by_field {
                let field_snapshot = index_snapshot
                    .request_result_cache_fields
                    .entry(field.clone())
                    .or_default();
                field_snapshot.request_result_cache_bytes = field_cache.resident_bytes;
                field_snapshot.request_result_cache_entries = field_cache.entries.len();
                field_snapshot.request_result_cache_hits = field_cache.hits;
                field_snapshot.request_result_cache_misses = field_cache.misses;
                field_snapshot.request_result_cache_evictions = field_cache.evictions;
                field_snapshot.request_result_cache_capacity_evictions =
                    field_cache.capacity_evictions;
                field_snapshot.request_result_cache_resets = field_cache.resets;
                field_snapshot.request_result_cache_invalidated_entries =
                    field_cache.invalidated_entries;
                field_snapshot.request_result_cache_refresh_invalidations =
                    field_cache.refresh_invalidations;
                field_snapshot.request_result_cache_stale_invalidations =
                    field_cache.stale_invalidations;
                (
                    field_snapshot.request_result_cache_oldest_entry_age_ticks,
                    field_snapshot.request_result_cache_newest_entry_age_ticks,
                ) = resident_entry_age_bounds(
                    current_tick,
                    field_cache.entries.values().map(|entry| entry.last_access_tick),
                );
            }

            index_snapshot.summary.vector_graph_cache_bytes =
                index.runtime_cache.vector_graph_by_field.resident_bytes;
            index_snapshot.summary.vector_graph_cache_entries =
                index.runtime_cache.vector_graph_by_field.entries.len();
            index_snapshot.summary.vector_graph_cache_hits =
                index.runtime_cache.vector_graph_by_field.hits;
            index_snapshot.summary.vector_graph_cache_misses =
                index.runtime_cache.vector_graph_by_field.misses;
            index_snapshot.summary.vector_graph_cache_evictions =
                index.runtime_cache.vector_graph_by_field.evictions;
            index_snapshot.summary.vector_graph_cache_capacity_evictions =
                index.runtime_cache.vector_graph_by_field.capacity_evictions;
            index_snapshot.summary.vector_graph_cache_resets =
                index.runtime_cache.vector_graph_by_field.resets;
            index_snapshot.summary.vector_graph_cache_invalidated_entries =
                index.runtime_cache.vector_graph_by_field.invalidated_entries;
            index_snapshot.summary.vector_graph_cache_refresh_invalidations =
                index.runtime_cache.vector_graph_by_field.refresh_invalidations;
            index_snapshot.summary.vector_graph_cache_stale_invalidations =
                index.runtime_cache.vector_graph_by_field.stale_invalidations;
            (
                index_snapshot.vector_graph_cache_oldest_entry_age_ticks,
                index_snapshot.vector_graph_cache_newest_entry_age_ticks,
            ) = resident_entry_age_bounds(
                current_tick,
                index
                    .runtime_cache
                    .vector_graph_by_field
                    .entries
                    .values()
                    .map(|entry| entry.last_access_tick),
            );
            for (field, entry) in &index.runtime_cache.vector_graph_by_field.entries {
                let field_snapshot = index_snapshot
                    .vector_graph_cache_fields
                    .entry(field.clone())
                    .or_default();
                let telemetry = index
                    .runtime_cache
                    .vector_graph_by_field
                    .telemetry_by_field
                    .get(field)
                    .cloned()
                    .unwrap_or_default();
                field_snapshot.vector_graph_cache_bytes = entry.resident_bytes;
                field_snapshot.vector_graph_cache_entries = 1;
                field_snapshot.vector_graph_cache_hits = telemetry.hits;
                field_snapshot.vector_graph_cache_misses = telemetry.misses;
                field_snapshot.vector_graph_cache_evictions = telemetry.evictions;
                field_snapshot.vector_graph_cache_capacity_evictions =
                    telemetry.capacity_evictions;
                field_snapshot.vector_graph_cache_resets = telemetry.resets;
                field_snapshot.vector_graph_cache_invalidated_entries =
                    telemetry.invalidated_entries;
                field_snapshot.vector_graph_cache_refresh_invalidations =
                    telemetry.refresh_invalidations;
                field_snapshot.vector_graph_cache_stale_invalidations =
                    telemetry.stale_invalidations;
                let age = current_tick.saturating_sub(entry.last_access_tick);
                field_snapshot.vector_graph_cache_oldest_entry_age_ticks = age;
                field_snapshot.vector_graph_cache_newest_entry_age_ticks = age;
            }
            for (field, telemetry) in &index.runtime_cache.vector_graph_by_field.telemetry_by_field {
                let field_snapshot = index_snapshot
                    .vector_graph_cache_fields
                    .entry(field.clone())
                    .or_default();
                field_snapshot.vector_graph_cache_hits = telemetry.hits;
                field_snapshot.vector_graph_cache_misses = telemetry.misses;
                field_snapshot.vector_graph_cache_evictions = telemetry.evictions;
                field_snapshot.vector_graph_cache_capacity_evictions =
                    telemetry.capacity_evictions;
                field_snapshot.vector_graph_cache_resets = telemetry.resets;
                field_snapshot.vector_graph_cache_invalidated_entries =
                    telemetry.invalidated_entries;
                field_snapshot.vector_graph_cache_refresh_invalidations =
                    telemetry.refresh_invalidations;
                field_snapshot.vector_graph_cache_stale_invalidations =
                    telemetry.stale_invalidations;
            }

            index_snapshot.summary.fast_field_cache_bytes =
                index.runtime_cache.fast_fields_by_name.resident_bytes;
            index_snapshot.summary.fast_field_cache_entries =
                index.runtime_cache.fast_fields_by_name.entries.len();
            index_snapshot.summary.fast_field_cache_hits =
                index.runtime_cache.fast_fields_by_name.hits;
            index_snapshot.summary.fast_field_cache_misses =
                index.runtime_cache.fast_fields_by_name.misses;
            index_snapshot.summary.fast_field_cache_evictions =
                index.runtime_cache.fast_fields_by_name.evictions;
            index_snapshot.summary.fast_field_cache_capacity_evictions =
                index.runtime_cache.fast_fields_by_name.capacity_evictions;
            index_snapshot.summary.fast_field_cache_resets =
                index.runtime_cache.fast_fields_by_name.resets;
            index_snapshot.summary.fast_field_cache_invalidated_entries =
                index.runtime_cache.fast_fields_by_name.invalidated_entries;
            index_snapshot.summary.fast_field_cache_refresh_invalidations =
                index.runtime_cache.fast_fields_by_name.refresh_invalidations;
            index_snapshot.summary.fast_field_cache_stale_invalidations =
                index.runtime_cache.fast_fields_by_name.stale_invalidations;
            (
                index_snapshot.fast_field_cache_oldest_entry_age_ticks,
                index_snapshot.fast_field_cache_newest_entry_age_ticks,
            ) = resident_entry_age_bounds(
                current_tick,
                index
                    .runtime_cache
                    .fast_fields_by_name
                    .entries
                    .values()
                    .map(|entry| entry.last_access_tick),
            );
            for (field, entry) in &index.runtime_cache.fast_fields_by_name.entries {
                let field_snapshot = index_snapshot
                    .fast_field_cache_fields
                    .entry(field.clone())
                    .or_default();
                let telemetry = index
                    .runtime_cache
                    .fast_fields_by_name
                    .telemetry_by_field
                    .get(field)
                    .cloned()
                    .unwrap_or_default();
                field_snapshot.fast_field_cache_bytes = entry.resident_bytes;
                field_snapshot.fast_field_cache_entries = 1;
                field_snapshot.fast_field_cache_hits = telemetry.hits;
                field_snapshot.fast_field_cache_misses = telemetry.misses;
                field_snapshot.fast_field_cache_evictions = telemetry.evictions;
                field_snapshot.fast_field_cache_capacity_evictions =
                    telemetry.capacity_evictions;
                field_snapshot.fast_field_cache_resets = telemetry.resets;
                field_snapshot.fast_field_cache_invalidated_entries =
                    telemetry.invalidated_entries;
                field_snapshot.fast_field_cache_refresh_invalidations =
                    telemetry.refresh_invalidations;
                field_snapshot.fast_field_cache_stale_invalidations =
                    telemetry.stale_invalidations;
                let age = current_tick.saturating_sub(entry.last_access_tick);
                field_snapshot.fast_field_cache_oldest_entry_age_ticks = age;
                field_snapshot.fast_field_cache_newest_entry_age_ticks = age;
            }
            for (field, telemetry) in &index.runtime_cache.fast_fields_by_name.telemetry_by_field {
                let field_snapshot = index_snapshot
                    .fast_field_cache_fields
                    .entry(field.clone())
                    .or_default();
                field_snapshot.fast_field_cache_hits = telemetry.hits;
                field_snapshot.fast_field_cache_misses = telemetry.misses;
                field_snapshot.fast_field_cache_evictions = telemetry.evictions;
                field_snapshot.fast_field_cache_capacity_evictions =
                    telemetry.capacity_evictions;
                field_snapshot.fast_field_cache_resets = telemetry.resets;
                field_snapshot.fast_field_cache_invalidated_entries =
                    telemetry.invalidated_entries;
                field_snapshot.fast_field_cache_refresh_invalidations =
                    telemetry.refresh_invalidations;
                field_snapshot.fast_field_cache_stale_invalidations =
                    telemetry.stale_invalidations;
            }

            details
                .indices
                .insert(index.index_name.clone(), index_snapshot);
        }
        Ok(details)
    }

    fn search(&self, request: SearchRequest) -> EngineResult<SearchResponse> {
        let query = parse_query(&request.query)
            .map_err(|error| invalid_request(format!("failed to parse query: {error}")))?;
        let aggregation_map = parse_search_aggregation_map(&request.aggregations)?;
        let mut store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let index_names = if request.indices.is_empty() {
            store.indices.keys().cloned().collect::<Vec<_>>()
        } else {
            request.indices
        };

        let mut all_hits = Vec::new();
        let mut hits = Vec::new();
        for index_name in index_names {
            let Some(index) = store.indices.get_mut(&index_name) else {
                return Err(EngineError::IndexNotFound { index: index_name });
            };
            all_hits.extend(index.search_hits_for_query(&index_name, &Query::MatchAll)?);
            hits.extend(index.search_hits_for_query(&index_name, &query)?);
            index.touch_search_runtime_caches(&query, &request.sort, &aggregation_map);
        }

        let total_hits = hits.len() as u64;
        let aggregations = collect_aggregations(&hits, &all_hits, &aggregation_map);
        if request.sort.is_empty() && query_uses_vector_scores(&query) {
            hits.sort_by(|left, right| {
                right
                    .score
                    .partial_cmp(&left.score)
                    .unwrap_or(std::cmp::Ordering::Equal)
                    .then_with(|| left.metadata.id.cmp(&right.metadata.id))
            });
        } else {
            sort_hits(&mut hits, &request.sort);
        }
        let hits = hits
            .into_iter()
            .skip(request.from)
            .take(request.size)
            .collect();
        let fetch_subphases = vec![
            SearchFetchSubphaseResult::completed(
                SearchFetchSubphase::Source,
                "loaded _source for returned hits",
            ),
            SearchFetchSubphaseResult::completed(
                SearchFetchSubphase::Version,
                "attached document versions",
            ),
            SearchFetchSubphaseResult::completed(
                SearchFetchSubphase::SeqNoPrimaryTerm,
                "attached sequence numbers and primary terms",
            ),
            SearchFetchSubphaseResult::skipped(
                SearchFetchSubphase::StoredFields,
                "stored fields are not yet requested separately from _source",
            ),
            SearchFetchSubphaseResult::skipped(
                SearchFetchSubphase::Highlight,
                "highlight execution is not yet implemented",
            ),
            SearchFetchSubphaseResult::skipped(
                SearchFetchSubphase::Explain,
                "explain execution is not yet implemented",
            ),
        ];

        Ok(SearchResponse::new(total_hits, hits, aggregations)
            .with_phase_results(vec![
                SearchPhaseResult::completed(SearchPhase::CanMatch, "validated target indices"),
                SearchPhaseResult::completed(SearchPhase::Query, "matched refreshed documents"),
                SearchPhaseResult::completed(SearchPhase::Fetch, "materialized requested hits"),
                SearchPhaseResult::skipped(
                    SearchPhase::Dfs,
                    "single-node execution does not require distributed DFS",
                ),
            ])
            .with_fetch_subphases(fetch_subphases))
    }

    fn persist_shard_state(&self, index: &str, shard_path: &Path) -> EngineResult<ShardManifest> {
        TantivyEngine::persist_shard_state(self, index, shard_path)
    }

    fn recover_index_from_manifest(
        &self,
        index: String,
        request: CreateIndexRequest,
        shard_path: &Path,
    ) -> EngineResult<ShardManifest> {
        let schema = map_opensearch_index_to_tantivy_schema(&request)?;
        TantivyEngine::recover_index_from_manifest(self, index, schema, shard_path)
    }
}

impl TantivyEngine {
    pub fn index_schema(&self, index: &str) -> Option<TantivyIndexSchema> {
        self.store
            .lock()
            .expect("tantivy engine store mutex poisoned")
            .indices
            .get(index)
            .map(|stored| stored.schema.clone())
    }

    pub fn shard_manifest(&self, index: &str) -> EngineResult<ShardManifest> {
        let store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let Some(stored) = store.indices.get(index) else {
            return Err(EngineError::IndexNotFound {
                index: index.to_string(),
            });
        };

        Ok(stored.shard_manifest())
    }

    pub fn vector_segment_metadata(&self, index: &str) -> EngineResult<Vec<VectorSegmentMetadata>> {
        let store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let Some(stored) = store.indices.get(index) else {
            return Err(EngineError::IndexNotFound {
                index: index.to_string(),
            });
        };
        Ok(stored.vector_segment_metadata())
    }

    pub fn exact_vector_search(
        &self,
        index: &str,
        field: &str,
        query_vector: &[VectorValue],
        k: usize,
    ) -> EngineResult<Vec<VectorSearchHit>> {
        let store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let Some(stored) = store.indices.get(index) else {
            return Err(EngineError::IndexNotFound {
                index: index.to_string(),
            });
        };
        stored.exact_vector_search(field, query_vector, k)
    }

    pub fn hnsw_index_snapshot(
        &self,
        index: &str,
        field: &str,
        max_neighbors: usize,
    ) -> EngineResult<NativeHnswIndexSnapshot> {
        let store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let Some(stored) = store.indices.get(index) else {
            return Err(EngineError::IndexNotFound {
                index: index.to_string(),
            });
        };
        stored.hnsw_index_snapshot(field, max_neighbors)
    }

    pub fn hnsw_vector_search(
        &self,
        index: &str,
        field: &str,
        query_vector: &[VectorValue],
        k: usize,
        ef_search: usize,
    ) -> EngineResult<Vec<VectorSearchHit>> {
        let store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let Some(stored) = store.indices.get(index) else {
            return Err(EngineError::IndexNotFound {
                index: index.to_string(),
            });
        };
        stored.hnsw_vector_search(field, query_vector, k, ef_search)
    }

    pub fn persist_shard_manifest(
        &self,
        index: &str,
        shard_path: impl AsRef<Path>,
    ) -> EngineResult<ShardManifest> {
        let manifest = self.shard_manifest(index)?;
        persist_shard_manifest(shard_path, &manifest)?;
        Ok(manifest)
    }

    pub fn persist_shard_state(
        &self,
        index: &str,
        shard_path: impl AsRef<Path>,
    ) -> EngineResult<ShardManifest> {
        let shard_path = shard_path.as_ref();
        let operations = self.persisted_operations(index)?;
        persist_operations(shard_path, &operations)?;
        self.persist_shard_manifest(index, shard_path)
    }

    pub fn recover_index_from_manifest(
        &self,
        index: impl Into<String>,
        mut schema: TantivyIndexSchema,
        shard_path: impl AsRef<Path>,
    ) -> EngineResult<ShardManifest> {
        let index = index.into();
        let shard_path = shard_path.as_ref();
        let manifest = load_shard_manifest(shard_path)?;
        let documents = replay_operations(shard_path, &manifest)?;
        for document in documents.values() {
            ensure_dynamic_mappings_for_schema(&mut schema, &document.source)?;
        }
        validate_recovered_vector_state(&manifest, &schema, &documents)?;
        let expected_schema_hash = schema_hash(&index, &schema)?;
        if manifest.schema_hash != expected_schema_hash {
            return Err(EngineError::InvalidRequest {
                reason: format!(
                    "shard manifest schema hash [{}] does not match recovered schema hash [{}]",
                    manifest.schema_hash, expected_schema_hash
                ),
            });
        }

        let mut store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        if store.indices.contains_key(&index) {
            return Err(EngineError::IndexAlreadyExists { index });
        }

        let next_seq_no = manifest.max_sequence_number.saturating_add(1).max(
            documents
                .values()
                .map(|document| document.metadata.seq_no + 1)
                .max()
                .unwrap_or(0),
        );

        store.indices.insert(
            index.clone(),
            StoredIndex {
                index_name: index.clone(),
                index_uuid: manifest.index_uuid.clone(),
                allocation_id: manifest.allocation_id.clone(),
                schema,
                schema_hash: manifest.schema_hash,
                documents,
                next_seq_no,
                refreshed_seq_no: manifest.refreshed_sequence_number,
                primary_term: manifest.primary_term,
                committed_generation: manifest.committed_generation,
                translog_generation: manifest.translog_generation,
                collector_telemetry: SearchCollectorTelemetry::default(),
                runtime_cache: SearchRuntimeCache::default(),
            },
        );

        Ok(manifest)
    }

    fn persisted_operations(&self, index: &str) -> EngineResult<Vec<PersistedDocumentOperation>> {
        let store = self
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let Some(stored) = store.indices.get(index) else {
            return Err(EngineError::IndexNotFound {
                index: index.to_string(),
            });
        };
        Ok(stored
            .documents
            .values()
            .map(|document| PersistedDocumentOperation {
                metadata: document.metadata.clone(),
                coordination: document.coordination.clone(),
                vector_fields: document.vector_fields.clone(),
                source: document.source.clone(),
            })
            .collect())
    }

    fn apply_write_refresh_policy(
        &self,
        index: &str,
        refresh_policy: RefreshPolicy,
    ) -> EngineResult<()> {
        match refresh_policy {
            RefreshPolicy::None => Ok(()),
            RefreshPolicy::Immediate | RefreshPolicy::WaitFor => {
                self.refresh(RefreshRequest {
                    indices: vec![index.to_string()],
                })?;
                Ok(())
            }
        }
    }
}

impl StoredIndex {
    fn ensure_dynamic_mappings(&mut self, source: &Value) -> EngineResult<()> {
        if ensure_dynamic_mappings_for_schema(&mut self.schema, source)? {
            self.schema_hash = schema_hash(&self.index_name, &self.schema)?;
        }
        Ok(())
    }

    fn apply_primary_document(
        &mut self,
        id: String,
        source: Value,
    ) -> (DocumentMetadata, WriteCoordinationMetadata, WriteResult) {
        self.apply_primary_document_with_version(id, source, None)
    }

    fn apply_primary_document_with_version(
        &mut self,
        id: String,
        source: Value,
        version_override: Option<u64>,
    ) -> (DocumentMetadata, WriteCoordinationMetadata, WriteResult) {
        let previous = self.documents.get(&id);
        let version = version_override.unwrap_or_else(|| {
            previous
                .map(|document| document.metadata.version + 1)
                .unwrap_or(1)
        });
        let result = if previous.is_some() {
            WriteResult::Updated
        } else {
            WriteResult::Created
        };
        let metadata = DocumentMetadata {
            id: id.clone(),
            version,
            seq_no: self.next_seq_no,
            primary_term: self.primary_term,
        };
        self.next_seq_no += 1;
        let local_checkpoint = self.next_seq_no - 1;
        let coordination = WriteCoordinationMetadata {
            translog_location: Some(TranslogLocation {
                generation: self.translog_generation,
                offset: metadata.seq_no as u64,
                size: 1,
            }),
            global_checkpoint: local_checkpoint,
            local_checkpoint,
            retention_leases: Vec::new(),
            noop: false,
        };
        self.documents.insert(
            id,
            StoredDocument {
                metadata: metadata.clone(),
                coordination: coordination.clone(),
                vector_fields: extract_vector_fields(&self.schema, &source),
                source,
            },
        );
        (metadata, coordination, result)
    }

    fn apply_replayed_document(
        &mut self,
        metadata: DocumentMetadata,
        coordination: WriteCoordinationMetadata,
        source: Value,
    ) -> EngineResult<WriteResult> {
        if metadata.id.is_empty() {
            return Err(invalid_request(
                "replayed document metadata id must not be empty",
            ));
        }
        if metadata.version == 0 {
            return Err(invalid_request(
                "replayed document metadata version must be greater than zero",
            ));
        }
        if metadata.seq_no < 0 {
            return Err(invalid_request(
                "replayed document metadata seq_no must be non-negative",
            ));
        }
        if metadata.primary_term == 0 {
            return Err(invalid_request(
                "replayed document metadata primary_term must be greater than zero",
            ));
        }

        if let Some(existing) = self.documents.get(&metadata.id) {
            if existing.metadata.seq_no > metadata.seq_no {
                return Err(invalid_request(format!(
                    "replayed document seq_no [{}] is older than existing seq_no [{}] for id [{}]",
                    metadata.seq_no, existing.metadata.seq_no, metadata.id
                )));
            }
        }

        let result = if self.documents.contains_key(&metadata.id) {
            WriteResult::Updated
        } else {
            WriteResult::Created
        };
        self.next_seq_no = self.next_seq_no.max(metadata.seq_no.saturating_add(1));
        self.primary_term = self.primary_term.max(metadata.primary_term);
        self.documents.insert(
            metadata.id.clone(),
            StoredDocument {
                vector_fields: extract_vector_fields(&self.schema, &source),
                metadata,
                coordination,
                source,
            },
        );
        Ok(result)
    }

    fn apply_update_document(
        &mut self,
        id: &str,
        doc: Value,
        doc_as_upsert: bool,
    ) -> Option<(DocumentMetadata, WriteCoordinationMetadata, WriteResult)> {
        self.apply_update_document_with_version(id, doc, doc_as_upsert, None)
    }

    fn apply_update_document_with_version(
        &mut self,
        id: &str,
        doc: Value,
        doc_as_upsert: bool,
        version_override: Option<u64>,
    ) -> Option<(DocumentMetadata, WriteCoordinationMetadata, WriteResult)> {
        let (version, source, result) = match self.documents.get(id) {
            Some(previous) => {
                let mut source = previous.source.clone();
                merge_update_document(&mut source, doc);
                (
                    version_override.unwrap_or(previous.metadata.version + 1),
                    source,
                    WriteResult::Updated,
                )
            }
            None if doc_as_upsert => (version_override.unwrap_or(1), doc, WriteResult::Created),
            None => return None,
        };

        let metadata = DocumentMetadata {
            id: id.to_string(),
            version,
            seq_no: self.next_seq_no,
            primary_term: self.primary_term,
        };
        self.next_seq_no += 1;
        let local_checkpoint = self.next_seq_no - 1;
        let coordination = WriteCoordinationMetadata {
            translog_location: Some(TranslogLocation {
                generation: self.translog_generation,
                offset: metadata.seq_no as u64,
                size: 1,
            }),
            global_checkpoint: local_checkpoint,
            local_checkpoint,
            retention_leases: Vec::new(),
            noop: false,
        };
        self.documents.insert(
            id.to_string(),
            StoredDocument {
                metadata: metadata.clone(),
                coordination: coordination.clone(),
                vector_fields: extract_vector_fields(&self.schema, &source),
                source,
            },
        );
        Some((metadata, coordination, result))
    }

    fn apply_delete_document(
        &mut self,
        id: &str,
    ) -> Option<(DocumentMetadata, WriteCoordinationMetadata)> {
        self.apply_delete_document_with_version(id, None)
    }

    fn apply_delete_document_with_version(
        &mut self,
        id: &str,
        version_override: Option<u64>,
    ) -> Option<(DocumentMetadata, WriteCoordinationMetadata)> {
        let previous = self.documents.remove(id)?;
        let metadata = DocumentMetadata {
            id: id.to_string(),
            version: version_override.unwrap_or(previous.metadata.version + 1),
            seq_no: self.next_seq_no,
            primary_term: self.primary_term,
        };
        self.next_seq_no += 1;
        let local_checkpoint = self.next_seq_no - 1;
        let coordination = WriteCoordinationMetadata {
            translog_location: Some(TranslogLocation {
                generation: self.translog_generation,
                offset: metadata.seq_no as u64,
                size: 1,
            }),
            global_checkpoint: local_checkpoint,
            local_checkpoint,
            retention_leases: previous.coordination.retention_leases,
            noop: false,
        };
        Some((metadata, coordination))
    }

    fn shard_manifest(&self) -> ShardManifest {
        let max_sequence_number = self.next_seq_no - 1;
        ShardManifest {
            index_uuid: self.index_uuid.clone(),
            shard_id: 0,
            allocation_id: self.allocation_id.clone(),
            primary_term: self.primary_term,
            max_sequence_number,
            local_checkpoint: max_sequence_number,
            refreshed_sequence_number: self.refreshed_seq_no,
            committed_generation: self.committed_generation,
            translog_generation: self.translog_generation,
            schema_hash: self.schema_hash,
            vector_segments: self.vector_segment_metadata(),
        }
    }

    fn vector_segment_metadata(&self) -> Vec<VectorSegmentMetadata> {
        self.schema
            .fields
            .iter()
            .filter_map(|field| {
                let mapping = field.knn_vector.as_ref()?;
                let vector_count = self
                    .documents
                    .values()
                    .filter(|document| document.vector_fields.contains_key(&field.name))
                    .count();
                Some(VectorSegmentMetadata {
                    field: field.name.clone(),
                    dimension: mapping.dimension,
                    document_count: self.documents.len(),
                    vector_count,
                    vector_format: KNN_VECTOR_FORMAT.to_string(),
                    ann_graph: Some("steelsearch-native-hnsw".to_string()),
                })
            })
            .collect()
    }

    fn knn_mapping(&self, field: &str) -> EngineResult<&KnnVectorMapping> {
        self.schema
            .fields
            .iter()
            .find(|mapping| mapping.name == field)
            .and_then(|mapping| mapping.knn_vector.as_ref())
            .ok_or_else(|| invalid_request(format!("field [{field}] is not a knn_vector field")))
    }

    fn exact_vector_search(
        &self,
        field: &str,
        query_vector: &[VectorValue],
        k: usize,
    ) -> EngineResult<Vec<VectorSearchHit>> {
        let mapping = self.knn_mapping(field)?;
        validate_knn_execution_mapping(field, mapping)?;
        validate_vector_dimension(field, mapping.dimension, query_vector)?;
        let mut hits = self
            .documents
            .values()
            .filter(|document| document.metadata.seq_no <= self.refreshed_seq_no)
            .filter_map(|document| {
                let vector = document.vector_fields.get(field)?;
                Some(VectorSearchHit {
                    id: document.metadata.id.clone(),
                    score: score_vector(mapping, query_vector, &vector.values),
                    source: document.source.clone(),
                })
            })
            .collect::<Vec<_>>();
        sort_vector_hits(&mut hits);
        hits.truncate(k);
        Ok(hits)
    }

    fn hnsw_index_snapshot(
        &self,
        field: &str,
        max_neighbors: usize,
    ) -> EngineResult<NativeHnswIndexSnapshot> {
        let mapping = self.knn_mapping(field)?;
        validate_knn_execution_mapping(field, mapping)?;
        let max_neighbors = max_neighbors.max(1);
        let documents = self
            .documents
            .values()
            .filter(|document| document.metadata.seq_no <= self.refreshed_seq_no)
            .filter(|document| document.vector_fields.contains_key(field))
            .collect::<Vec<_>>();
        let nodes = documents
            .iter()
            .map(|document| {
                let vector = &document.vector_fields[field].values;
                let mut neighbors = documents
                    .iter()
                    .filter(|candidate| candidate.metadata.id != document.metadata.id)
                    .map(|candidate| {
                        (
                            candidate.metadata.id.clone(),
                            score_vector(mapping, vector, &candidate.vector_fields[field].values),
                        )
                    })
                    .collect::<Vec<_>>();
                neighbors.sort_by(|left, right| {
                    right
                        .1
                        .partial_cmp(&left.1)
                        .unwrap_or(std::cmp::Ordering::Equal)
                });
                NativeHnswNodeSnapshot {
                    id: document.metadata.id.clone(),
                    neighbors: neighbors
                        .into_iter()
                        .take(max_neighbors)
                        .map(|(id, _)| id)
                        .collect(),
                }
            })
            .collect();

        Ok(NativeHnswIndexSnapshot {
            field: field.to_string(),
            dimension: mapping.dimension,
            nodes,
        })
    }

    fn hnsw_vector_search(
        &self,
        field: &str,
        query_vector: &[VectorValue],
        k: usize,
        ef_search: usize,
    ) -> EngineResult<Vec<VectorSearchHit>> {
        let mapping = self.knn_mapping(field)?;
        validate_knn_execution_mapping(field, mapping)?;
        validate_vector_dimension(field, mapping.dimension, query_vector)?;
        let graph = self.hnsw_index_snapshot(field, ef_search.max(k).max(1))?;
        let Some(entrypoint) = graph.nodes.first() else {
            return Ok(Vec::new());
        };
        let neighbors_by_id = graph
            .nodes
            .iter()
            .map(|node| (node.id.as_str(), node.neighbors.as_slice()))
            .collect::<BTreeMap<_, _>>();
        let mut frontier = vec![entrypoint.id.clone()];
        let mut visited = BTreeMap::<String, f32>::new();

        while let Some(id) = frontier.pop() {
            if visited.contains_key(&id) || visited.len() >= ef_search.max(k).max(1) {
                continue;
            }
            let Some(document) = self.documents.get(&id) else {
                continue;
            };
            let Some(vector) = document.vector_fields.get(field) else {
                continue;
            };
            visited.insert(
                id.clone(),
                score_vector(mapping, query_vector, &vector.values),
            );
            if let Some(neighbors) = neighbors_by_id.get(id.as_str()) {
                frontier.extend(
                    neighbors
                        .iter()
                        .rev()
                        .filter(|neighbor| !visited.contains_key(*neighbor))
                        .map(|neighbor| (*neighbor).clone()),
                );
            }
        }

        let mut hits = visited
            .into_iter()
            .filter_map(|(id, score)| {
                let document = self.documents.get(&id)?;
                Some(VectorSearchHit {
                    id,
                    score,
                    source: document.source.clone(),
                })
            })
            .collect::<Vec<_>>();
        sort_vector_hits(&mut hits);
        hits.truncate(k);
        Ok(hits)
    }

    fn search_hits_for_query(
        &mut self,
        index_name: &str,
        query: &Query,
    ) -> EngineResult<Vec<SearchHit>> {
        if let Query::Knn(knn) = query {
            if let Some(cached_hits) = self.lookup_cached_knn_search(knn) {
                self.collector_telemetry.knn_collector_bytes_by_field.insert(
                    knn.field.clone(),
                    cached_hits
                        .len()
                        .saturating_mul(std::mem::size_of::<SearchHit>())
                        .saturating_add(
                            knn.vector
                                .len()
                                .saturating_mul(std::mem::size_of::<VectorValue>()),
                        ),
                );
                return Ok(cached_hits);
            }
        }

        let mut hits = self
            .documents
            .values()
            .filter(|document| document.metadata.seq_no <= self.refreshed_seq_no)
            .map(|document| {
                self.score_document_query(query, document).map(|score| {
                    score.map(|score| SearchHit {
                        index: index_name.to_string(),
                        metadata: document.metadata.clone(),
                        score,
                        source: document.source.clone(),
                    })
                })
            })
            .collect::<EngineResult<Vec<_>>>()?
            .into_iter()
            .flatten()
            .collect::<Vec<_>>();
        if let Query::Knn(knn) = query {
            self.collector_telemetry.knn_collector_bytes_by_field.insert(
                knn.field.clone(),
                hits.len()
                    .saturating_mul(std::mem::size_of::<SearchHit>())
                    .saturating_add(
                        knn.vector
                            .len()
                            .saturating_mul(std::mem::size_of::<VectorValue>()),
                    ),
            );
            hits.sort_by(|left, right| {
                right
                    .score
                    .partial_cmp(&left.score)
                    .unwrap_or(std::cmp::Ordering::Equal)
                    .then_with(|| left.metadata.id.cmp(&right.metadata.id))
            });
            hits.truncate(knn.k);
            self.cache_knn_search_result(knn, &hits);
        }
        Ok(hits)
    }

    fn lookup_cached_knn_search(&mut self, knn: &KnnQuery) -> Option<Vec<SearchHit>> {
        let cache_key = cached_knn_search_key(knn);
        let access_tick = self.runtime_cache.next_access_tick();
        let field_cache = self
            .runtime_cache
            .knn_search_by_field
            .entry(knn.field.clone())
            .or_default();
        let should_invalidate = match field_cache.entries.get(&cache_key) {
            Some(cached) => cached.refreshed_seq_no != self.refreshed_seq_no || cached.query != *knn,
            None => {
                field_cache.misses = field_cache.misses.saturating_add(1);
                return None;
            }
        };
        if should_invalidate {
            let cached = field_cache.entries.remove(&cache_key)?;
            field_cache.resident_bytes = field_cache
                .resident_bytes
                .saturating_sub(cached.resident_bytes);
            field_cache.misses = field_cache.misses.saturating_add(1);
            field_cache.invalidated_entries = field_cache.invalidated_entries.saturating_add(1);
            field_cache.stale_invalidations = field_cache.stale_invalidations.saturating_add(1);
            self.runtime_cache.request_result_invalidated_entries = self
                .runtime_cache
                .request_result_invalidated_entries
                .saturating_add(1);
            self.runtime_cache.request_result_stale_invalidations = self
                .runtime_cache
                .request_result_stale_invalidations
                .saturating_add(1);
            return None;
        }
        let cached = field_cache.entries.get_mut(&cache_key)?;
        cached.last_access_tick = access_tick;
        field_cache.hits = field_cache.hits.saturating_add(1);
        Some(cached.hits.clone())
    }

    fn cache_knn_search_result(&mut self, knn: &KnnQuery, hits: &[SearchHit]) {
        let cache_key = cached_knn_search_key(knn);
        let access_tick = self.runtime_cache.next_access_tick();
        let resident_bytes = cached_knn_search_entry_bytes(knn, hits);
        self.runtime_cache.insert_knn_entry(
            knn.field.clone(),
            cache_key,
            CachedKnnSearchEntry {
                refreshed_seq_no: self.refreshed_seq_no,
                query: knn.clone(),
                hits: hits.to_vec(),
                resident_bytes,
                last_access_tick: access_tick,
            },
        );
    }

    fn touch_search_runtime_caches(
        &mut self,
        query: &Query,
        sort: &[SortSpec],
        aggregations: &AggregationMap,
    ) {
        for knn_query in knn_queries(query) {
            self.runtime_cache.touch_vector_graph_cache(
                knn_query.field.clone(),
                visible_vector_bytes(self, &knn_query.field),
            );
        }
        for field_name in sort
            .iter()
            .map(|sort_spec| sort_spec.field.as_str())
            .chain(aggregation_field_names(aggregations).iter().map(String::as_str))
        {
            if self
                .schema
                .fields
                .iter()
                .any(|field| field.name == field_name && field.fast)
            {
                self.runtime_cache.touch_fast_field_cache(
                    field_name.to_string(),
                    visible_field_value_bytes(self, field_name),
                );
            }
        }
    }

    fn score_document_query(
        &self,
        query: &Query,
        document: &StoredDocument,
    ) -> EngineResult<Option<f32>> {
        match query {
            Query::Knn(knn) => self.score_knn_query(knn, document),
            Query::Bool { clauses } => self.score_bool_query(clauses, document),
            _ => Ok(
                document_matches_query(query, &document.metadata.id, &document.source)
                    .then_some(1.0),
            ),
        }
    }

    fn score_knn_query(
        &self,
        knn: &KnnQuery,
        document: &StoredDocument,
    ) -> EngineResult<Option<f32>> {
        let mapping = match self.knn_mapping(&knn.field) {
            Ok(mapping) => mapping,
            Err(_) if knn.ignore_unmapped => return Ok(None),
            Err(error) => return Err(error),
        };
        validate_knn_execution_mapping(&knn.field, mapping)?;
        validate_vector_dimension(&knn.field, mapping.dimension, &knn.vector)?;
        if let Some(filter) = &knn.filter {
            if self.score_document_query(filter, document)?.is_none() {
                return Ok(None);
            }
        }
        let Some(vector) = document.vector_fields.get(&knn.field) else {
            return Ok(None);
        };
        let score = score_vector(mapping, &knn.vector, &vector.values);
        if let Some(min_score) = knn.min_score {
            if score < min_score {
                return Ok(None);
            }
        }
        if let Some(max_distance) = knn.max_distance {
            let distance = -score;
            if distance > max_distance {
                return Ok(None);
            }
        }
        Ok(Some(score))
    }

    fn score_bool_query(
        &self,
        clauses: &BoolQuery,
        document: &StoredDocument,
    ) -> EngineResult<Option<f32>> {
        let mut score = 0.0;
        for query in &clauses.must {
            let Some(query_score) = self.score_document_query(query, document)? else {
                return Ok(None);
            };
            score += query_score;
        }
        for query in &clauses.filter {
            if self.score_document_query(query, document)?.is_none() {
                return Ok(None);
            }
        }
        for query in &clauses.must_not {
            if self.score_document_query(query, document)?.is_some() {
                return Ok(None);
            }
        }
        let matched_should = clauses
            .should
            .iter()
            .map(|query| self.score_document_query(query, document))
            .collect::<EngineResult<Vec<_>>>()?;
        let should_count = matched_should
            .iter()
            .filter(|score| score.is_some())
            .count() as u32;
        let minimum_should_match = clauses.minimum_should_match.unwrap_or(u32::from(
            !clauses.should.is_empty() && clauses.must.is_empty(),
        ));
        if should_count < minimum_should_match {
            return Ok(None);
        }
        score += matched_should.into_iter().flatten().sum::<f32>();
        if score == 0.0 {
            score = 1.0;
        }
        Ok(Some(score))
    }
}

fn merge_update_document(source: &mut Value, doc: Value) {
    match (source, doc) {
        (Value::Object(source), Value::Object(doc)) => {
            for (field, value) in doc {
                source.insert(field, value);
            }
        }
        (source, doc) => *source = doc,
    }
}

fn infer_dynamic_field_type(value: &Value) -> Option<TantivyFieldType> {
    match value {
        Value::String(_) => Some(TantivyFieldType::Text),
        Value::Number(number) if number.is_i64() || number.is_u64() => Some(TantivyFieldType::I64),
        Value::Number(_) => Some(TantivyFieldType::F64),
        Value::Bool(_) => Some(TantivyFieldType::Bool),
        Value::Null | Value::Array(_) | Value::Object(_) => None,
    }
}

fn ensure_dynamic_mappings_for_schema(
    schema: &mut TantivyIndexSchema,
    source: &Value,
) -> EngineResult<bool> {
    let Some(fields) = source.as_object() else {
        return Ok(false);
    };

    let mut changed = false;
    for (name, value) in fields {
        if schema.fields.iter().any(|field| field.name == *name) {
            continue;
        }
        let Some(field_type) = infer_dynamic_field_type(value) else {
            continue;
        };
        if !schema.dynamic {
            return Err(invalid_request(format!(
                "dynamic mapping is disabled and field [{name}] is not mapped"
            )));
        }
        schema.fields.push(TantivyFieldMapping {
            name: name.clone(),
            indexed: true,
            stored: false,
            fast: matches!(
                field_type,
                TantivyFieldType::Keyword
                    | TantivyFieldType::I64
                    | TantivyFieldType::F64
                    | TantivyFieldType::Bool
                    | TantivyFieldType::Date
            ),
            field_type,
            knn_vector: None,
        });
        changed = true;
    }
    Ok(changed)
}

fn validate_write_condition(
    existing: Option<&StoredDocument>,
    condition: &WriteCondition,
) -> EngineResult<Option<u64>> {
    match (condition.if_seq_no, condition.if_primary_term) {
        (Some(if_seq_no), Some(if_primary_term)) => {
            let Some(existing) = existing else {
                return Err(version_conflict(
                    "required seq_no/primary_term but document is missing",
                ));
            };
            if existing.metadata.seq_no != if_seq_no
                || existing.metadata.primary_term != if_primary_term
            {
                return Err(version_conflict(format!(
                    "required seq_no [{}] and primary_term [{}], but current seq_no [{}] and primary_term [{}]",
                    if_seq_no,
                    if_primary_term,
                    existing.metadata.seq_no,
                    existing.metadata.primary_term
                )));
            }
        }
        (None, None) => {}
        _ => {
            return Err(invalid_request(
                "if_seq_no and if_primary_term must be supplied together",
            ));
        }
    }

    match condition.version_type {
        VersionType::Internal => {
            if let Some(required_version) = condition.version {
                let Some(existing) = existing else {
                    return Err(version_conflict(format!(
                        "required version [{}] but document is missing",
                        required_version
                    )));
                };
                if existing.metadata.version != required_version {
                    return Err(version_conflict(format!(
                        "required version [{}], but current version is [{}]",
                        required_version, existing.metadata.version
                    )));
                }
            }
            Ok(None)
        }
        VersionType::External | VersionType::ExternalGte => {
            let Some(version) = condition.version else {
                return Err(invalid_request(
                    "external versioning requires a version value",
                ));
            };
            if version == 0 {
                return Err(invalid_request(
                    "external version value must be greater than zero",
                ));
            }
            if let Some(existing) = existing {
                let allowed = match condition.version_type {
                    VersionType::External => version > existing.metadata.version,
                    VersionType::ExternalGte => version >= existing.metadata.version,
                    VersionType::Internal => unreachable!(),
                };
                if !allowed {
                    return Err(version_conflict(format!(
                        "external version [{}] is not newer than current version [{}]",
                        version, existing.metadata.version
                    )));
                }
            }
            Ok(Some(version))
        }
    }
}

fn version_conflict(reason: impl Into<String>) -> EngineError {
    EngineError::VersionConflict {
        reason: reason.into(),
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
struct PersistedDocumentOperation {
    metadata: DocumentMetadata,
    #[serde(default)]
    coordination: WriteCoordinationMetadata,
    #[serde(default)]
    vector_fields: BTreeMap<String, StoredVectorField>,
    #[serde(rename = "_source")]
    source: Value,
}

fn operations_path(shard_path: &Path) -> std::path::PathBuf {
    shard_path.join(SHARD_OPERATIONS_FILE_NAME)
}

fn persist_operations(
    shard_path: &Path,
    operations: &[PersistedDocumentOperation],
) -> EngineResult<()> {
    fs::create_dir_all(shard_path).map_err(|error| EngineError::BackendFailure {
        reason: format!(
            "failed to create shard path [{}]: {error}",
            shard_path.display()
        ),
    })?;
    let path = operations_path(shard_path);
    let temp_path = path.with_extension("jsonl.tmp");
    let mut file = fs::File::create(&temp_path).map_err(|error| EngineError::BackendFailure {
        reason: format!(
            "failed to create operation log temp file [{}]: {error}",
            temp_path.display()
        ),
    })?;
    for operation in operations {
        serde_json::to_writer(&mut file, operation).map_err(|error| {
            EngineError::BackendFailure {
                reason: format!("failed to serialize operation log record: {error}"),
            }
        })?;
        file.write_all(b"\n")
            .map_err(|error| EngineError::BackendFailure {
                reason: format!("failed to write operation log record: {error}"),
            })?;
    }
    file.sync_all()
        .map_err(|error| EngineError::BackendFailure {
            reason: format!(
                "failed to sync operation log temp file [{}]: {error}",
                temp_path.display()
            ),
        })?;
    fs::rename(&temp_path, &path).map_err(|error| EngineError::BackendFailure {
        reason: format!(
            "failed to commit operation log [{}]: {error}",
            path.display()
        ),
    })
}

fn replay_operations(
    shard_path: &Path,
    manifest: &ShardManifest,
) -> EngineResult<BTreeMap<String, StoredDocument>> {
    let path = operations_path(shard_path);
    if !path.exists() {
        if manifest.max_sequence_number >= 0 || !manifest.vector_segments.is_empty() {
            return Err(EngineError::BackendFailure {
                reason: format!(
                    "missing operation log [{}] for shard manifest max_sequence_number [{}]",
                    path.display(),
                    manifest.max_sequence_number
                ),
            });
        }
        return Ok(BTreeMap::new());
    }
    let file = fs::File::open(&path).map_err(|error| EngineError::BackendFailure {
        reason: format!("failed to open operation log [{}]: {error}", path.display()),
    })?;
    let mut documents = BTreeMap::new();
    for (line_number, line) in BufReader::new(file).lines().enumerate() {
        let line = line.map_err(|error| EngineError::BackendFailure {
            reason: format!(
                "failed to read operation log [{}] line {}: {error}",
                path.display(),
                line_number + 1
            ),
        })?;
        if line.trim().is_empty() {
            continue;
        }
        let operation =
            serde_json::from_str::<PersistedDocumentOperation>(&line).map_err(|error| {
                EngineError::BackendFailure {
                    reason: format!(
                        "failed to parse operation log [{}] line {}: {error}",
                        path.display(),
                        line_number + 1
                    ),
                }
            })?;
        if operation.metadata.seq_no > manifest.max_sequence_number {
            return Err(EngineError::BackendFailure {
                reason: format!(
                    "operation log seq_no [{}] is newer than manifest max_sequence_number [{}]",
                    operation.metadata.seq_no, manifest.max_sequence_number
                ),
            });
        }
        documents.insert(
            operation.metadata.id.clone(),
            StoredDocument {
                metadata: operation.metadata,
                coordination: operation.coordination,
                vector_fields: operation.vector_fields,
                source: operation.source,
            },
        );
    }
    Ok(documents)
}

fn validate_recovered_vector_state(
    manifest: &ShardManifest,
    schema: &TantivyIndexSchema,
    documents: &BTreeMap<String, StoredDocument>,
) -> EngineResult<()> {
    for document in documents.values() {
        for (field, vector) in &document.vector_fields {
            let Some(mapping) = schema
                .fields
                .iter()
                .find(|mapping| mapping.name == *field)
                .and_then(|mapping| mapping.knn_vector.as_ref())
            else {
                return Err(EngineError::BackendFailure {
                    reason: format!(
                        "operation log contains vector field [{field}] without a knn_vector mapping"
                    ),
                });
            };
            validate_vector_dimension(field, mapping.dimension, &vector.values)?;
        }
    }

    for segment in &manifest.vector_segments {
        let Some(mapping) = schema
            .fields
            .iter()
            .find(|mapping| mapping.name == segment.field)
            .and_then(|mapping| mapping.knn_vector.as_ref())
        else {
            return Err(EngineError::BackendFailure {
                reason: format!(
                    "manifest vector segment [{}] has no matching knn_vector mapping",
                    segment.field
                ),
            });
        };
        if segment.dimension != mapping.dimension {
            return Err(EngineError::BackendFailure {
                reason: format!(
                    "manifest vector segment [{}] dimension [{}] does not match mapping dimension [{}]",
                    segment.field, segment.dimension, mapping.dimension
                ),
            });
        }
        if segment.vector_format != KNN_VECTOR_FORMAT {
            return Err(EngineError::BackendFailure {
                reason: format!(
                    "manifest vector segment [{}] uses unsupported vector format [{}]",
                    segment.field, segment.vector_format
                ),
            });
        }
        if segment.ann_graph.as_deref() != Some("steelsearch-native-hnsw") {
            return Err(EngineError::BackendFailure {
                reason: format!(
                    "manifest vector segment [{}] has invalid HNSW graph metadata",
                    segment.field
                ),
            });
        }

        let vector_count = documents
            .values()
            .filter(|document| document.vector_fields.contains_key(&segment.field))
            .count();
        if segment.document_count != documents.len() || segment.vector_count != vector_count {
            return Err(EngineError::BackendFailure {
                reason: format!(
                    "manifest vector segment [{}] count mismatch: documents {}/{}, vectors {}/{}",
                    segment.field,
                    segment.document_count,
                    documents.len(),
                    segment.vector_count,
                    vector_count
                ),
            });
        }
    }

    Ok(())
}

fn schema_hash(index: &str, schema: &TantivyIndexSchema) -> EngineResult<u64> {
    let bytes = serde_json::to_vec(schema).map_err(|error| EngineError::BackendFailure {
        reason: format!("failed to serialize schema for hash: {error}"),
    })?;
    let mut hash = 0xcbf29ce484222325_u64;
    for byte in index.as_bytes().iter().chain(bytes.iter()) {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x100000001b3);
    }
    Ok(hash)
}

fn extract_vector_fields(
    schema: &TantivyIndexSchema,
    source: &Value,
) -> BTreeMap<String, StoredVectorField> {
    schema
        .fields
        .iter()
        .filter_map(|field| {
            let mapping = field.knn_vector.as_ref()?;
            let values = source
                .get(&field.name)
                .and_then(Value::as_array)?
                .iter()
                .map(Value::as_f64)
                .collect::<Option<Vec<_>>>()?
                .into_iter()
                .map(|value| value as VectorValue)
                .collect::<Vec<_>>();
            (values.len() == mapping.dimension)
                .then_some((field.name.clone(), StoredVectorField { values }))
        })
        .collect()
}

fn validate_vector_dimension(
    field: &str,
    dimension: usize,
    query_vector: &[VectorValue],
) -> EngineResult<()> {
    if query_vector.len() == dimension {
        Ok(())
    } else {
        Err(invalid_request(format!(
            "query vector for field [{field}] has dimension [{}], expected [{dimension}]",
            query_vector.len()
        )))
    }
}

fn validate_knn_execution_mapping(field: &str, mapping: &KnnVectorMapping) -> EngineResult<()> {
    match mapping.data_type {
        KnnVectorDataType::Float => {}
        KnnVectorDataType::Byte => {
            return Err(invalid_request(format!(
                "knn_vector field [{field}] data_type [byte] is not supported for production execution"
            )));
        }
        KnnVectorDataType::Binary => {
            return Err(invalid_request(format!(
                "knn_vector field [{field}] data_type [binary] is not supported for production execution"
            )));
        }
    }

    match vector_space_type(mapping) {
        "l2" | "cosine" | "cosinesimil" | "innerproduct" | "dot_product" => {}
        other => {
            return Err(invalid_request(format!(
                "unsupported knn_vector space_type [{other}] for field [{field}]"
            )));
        }
    }

    for engine in [
        mapping.engine.as_deref(),
        mapping
            .method
            .as_ref()
            .and_then(|method| method.engine.as_deref()),
    ]
    .into_iter()
    .flatten()
    {
        match engine {
            "lucene" => {}
            other => {
                return Err(invalid_request(format!(
                    "unsupported knn_vector engine [{other}] for field [{field}]"
                )));
            }
        }
    }

    if let Some(method) = &mapping.method {
        if let Some(name) = method.name.as_deref() {
            if name != "hnsw" {
                return Err(invalid_request(format!(
                    "unsupported knn_vector method [{name}] for field [{field}]"
                )));
            }
        }
        if !method.parameters.is_empty() {
            return Err(invalid_request(format!(
                "unsupported knn_vector method parameters for field [{field}]"
            )));
        }
    }

    if let Some(mode) = mapping.mode.as_deref() {
        return Err(invalid_request(format!(
            "unsupported knn_vector mode [{mode}] for field [{field}]"
        )));
    }
    if let Some(compression_level) = mapping.compression_level.as_deref() {
        return Err(invalid_request(format!(
            "unsupported knn_vector compression_level [{compression_level}] for field [{field}]"
        )));
    }

    Ok(())
}

fn score_vector(
    mapping: &KnnVectorMapping,
    left: &[VectorValue],
    right: &[VectorValue],
) -> VectorValue {
    match vector_space_type(mapping) {
        "cosinesimil" | "cosine" => cosine_similarity(left, right),
        "innerproduct" | "dot_product" => dot_product(left, right),
        _ => -squared_l2_distance(left, right),
    }
}

fn vector_space_type(mapping: &KnnVectorMapping) -> &str {
    mapping
        .space_type
        .as_deref()
        .or_else(|| {
            mapping
                .method
                .as_ref()
                .and_then(|method| method.space_type.as_deref())
        })
        .unwrap_or("l2")
}

fn squared_l2_distance(left: &[VectorValue], right: &[VectorValue]) -> VectorValue {
    left.iter()
        .zip(right)
        .map(|(left, right)| {
            let delta = left - right;
            delta * delta
        })
        .sum()
}

fn dot_product(left: &[VectorValue], right: &[VectorValue]) -> VectorValue {
    left.iter()
        .zip(right)
        .map(|(left, right)| left * right)
        .sum()
}

fn cosine_similarity(left: &[VectorValue], right: &[VectorValue]) -> VectorValue {
    let dot = dot_product(left, right);
    let left_norm = dot_product(left, left).sqrt();
    let right_norm = dot_product(right, right).sqrt();
    if left_norm == 0.0 || right_norm == 0.0 {
        0.0
    } else {
        dot / (left_norm * right_norm)
    }
}

fn sort_vector_hits(hits: &mut [VectorSearchHit]) {
    hits.sort_by(|left, right| {
        right
            .score
            .partial_cmp(&left.score)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| left.id.cmp(&right.id))
    });
}

fn estimate_doc_values_reservation_bytes(
    index: &StoredIndex,
    sort: &[SortSpec],
    aggregations: &AggregationMap,
) -> usize {
    let sort_bytes = sort
        .iter()
        .filter_map(|sort_spec| index.schema.fields.iter().find(|field| field.name == sort_spec.field))
        .filter(|field| field.fast)
        .map(|field| visible_field_value_bytes(index, &field.name))
        .sum::<usize>();
    let aggregation_bytes = aggregation_field_names(aggregations)
        .into_iter()
        .filter_map(|field_name| index.schema.fields.iter().find(|field| field.name == field_name))
        .filter(|field| field.fast)
        .map(|field| visible_field_value_bytes(index, &field.name).saturating_mul(2))
        .sum::<usize>();
    sort_bytes.saturating_add(aggregation_bytes)
}

fn visible_vector_reservation_bytes(index: &StoredIndex, query: &Query) -> usize {
    knn_queries(query)
        .into_iter()
        .filter_map(|knn_query| {
            let field = index
                .schema
                .fields
                .iter()
                .find(|field| field.name == knn_query.field)?;
            field.knn_vector.as_ref()?;
            Some(visible_vector_bytes(index, &field.name))
        })
        .sum()
}

fn collector_telemetry_bytes(index: &StoredIndex, query: &Query) -> usize {
    knn_queries(query)
        .into_iter()
        .map(|knn_query| last_knn_collector_bytes(index, &knn_query.field))
        .sum()
}

fn request_result_cache_bytes_for_query(index: &StoredIndex, query: &Query) -> usize {
    knn_queries(query)
        .into_iter()
        .map(|knn_query| {
            index
                .runtime_cache
                .knn_search_by_field
                .get(&knn_query.field)
                .map(|field_cache| field_cache.resident_bytes)
                .unwrap_or(0)
        })
        .sum()
}

fn vector_graph_cache_bytes_for_query(index: &StoredIndex, query: &Query) -> usize {
    knn_queries(query)
        .into_iter()
        .map(|knn_query| {
            index
                .runtime_cache
                .vector_graph_by_field
                .entries
                .get(&knn_query.field)
                .map(|entry| entry.resident_bytes)
                .unwrap_or(0)
        })
        .sum()
}

fn fast_field_cache_bytes_for_request(
    index: &StoredIndex,
    sort: &[SortSpec],
    aggregations: &AggregationMap,
) -> usize {
    sort
        .iter()
        .map(|sort_spec| sort_spec.field.as_str())
        .chain(aggregation_field_names(aggregations).iter().map(String::as_str))
        .filter_map(|field_name| {
            index
                .runtime_cache
                .fast_fields_by_name
                .entries
                .get(field_name)
                .map(|entry| entry.resident_bytes)
        })
        .sum()
}

fn cache_telemetry_bytes(
    index: &StoredIndex,
    query: &Query,
    sort: &[SortSpec],
    aggregations: &AggregationMap,
) -> usize {
    request_result_cache_bytes_for_query(index, query)
        .saturating_add(vector_graph_cache_bytes_for_query(index, query))
        .saturating_add(fast_field_cache_bytes_for_request(index, sort, aggregations))
}

fn visible_field_value_bytes(index: &StoredIndex, field_name: &str) -> usize {
    index
        .documents
        .values()
        .filter(|document| document.metadata.seq_no <= index.refreshed_seq_no)
        .filter_map(|document| document.source.get(field_name))
        .map(estimate_value_bytes)
        .sum()
}

fn visible_vector_bytes(index: &StoredIndex, field_name: &str) -> usize {
    index
        .documents
        .values()
        .filter(|document| document.metadata.seq_no <= index.refreshed_seq_no)
        .filter_map(|document| document.vector_fields.get(field_name))
        .map(|field| field.values.len().saturating_mul(std::mem::size_of::<f32>()))
        .sum()
}

fn last_knn_collector_bytes(index: &StoredIndex, field_name: &str) -> usize {
    index
        .collector_telemetry
        .knn_collector_bytes_by_field
        .get(field_name)
        .copied()
        .unwrap_or(0)
}

fn cached_knn_search_entry_bytes(query: &KnnQuery, hits: &[SearchHit]) -> usize {
    let query_bytes = query
        .vector
        .len()
        .saturating_mul(std::mem::size_of::<VectorValue>());
    let hit_bytes = hits
        .iter()
        .map(estimate_search_hit_bytes)
        .sum::<usize>();
    query_bytes.saturating_add(hit_bytes)
}

fn evict_knn_cache_entries(field_cache: &mut CachedKnnSearchFieldCache) {
    while field_cache.entries.len() > MAX_KNN_CACHE_ENTRIES_PER_FIELD
        || field_cache.resident_bytes > MAX_KNN_CACHE_BYTES_PER_FIELD
    {
        let Some((oldest_key, oldest_bytes)) = field_cache
            .entries
            .iter()
            .min_by_key(|(_, entry)| entry.last_access_tick)
            .map(|(key, entry)| (key.clone(), entry.resident_bytes))
        else {
            break;
        };
        field_cache.entries.remove(&oldest_key);
        field_cache.resident_bytes = field_cache.resident_bytes.saturating_sub(oldest_bytes);
        field_cache.evictions = field_cache.evictions.saturating_add(1);
        field_cache.capacity_evictions = field_cache.capacity_evictions.saturating_add(1);
    }
}

fn touch_resident_field_cache(
    cache: &mut CachedResidentFieldCache,
    field: String,
    entry: CachedResidentFieldCacheEntry,
) {
    let new_bytes = entry.resident_bytes;
    let telemetry = cache.telemetry_by_field.entry(field.clone()).or_default();
    match cache.entries.insert(field, entry) {
        Some(previous) => {
            cache.hits = cache.hits.saturating_add(1);
            telemetry.hits = telemetry.hits.saturating_add(1);
            cache.resident_bytes = cache.resident_bytes.saturating_sub(previous.resident_bytes);
        }
        None => {
            cache.misses = cache.misses.saturating_add(1);
            telemetry.misses = telemetry.misses.saturating_add(1);
        }
    }
    cache.resident_bytes = cache.resident_bytes.saturating_add(new_bytes);
    while cache.entries.len() > MAX_KNN_CACHE_ENTRIES_PER_FIELD {
        let Some(oldest_key) = cache
            .entries
            .iter()
            .min_by_key(|(_, entry)| entry.last_access_tick)
            .map(|(field, _)| field.clone())
        else {
            break;
        };
        if let Some(previous) = cache.entries.remove(&oldest_key) {
            cache.resident_bytes = cache.resident_bytes.saturating_sub(previous.resident_bytes);
            cache.evictions = cache.evictions.saturating_add(1);
            cache.capacity_evictions = cache.capacity_evictions.saturating_add(1);
            let telemetry = cache.telemetry_by_field.entry(oldest_key).or_default();
            telemetry.evictions = telemetry.evictions.saturating_add(1);
            telemetry.capacity_evictions = telemetry.capacity_evictions.saturating_add(1);
        }
    }
}

fn cached_knn_search_key(query: &KnnQuery) -> String {
    serde_json::to_string(query).unwrap_or_else(|_| format!("{query:?}"))
}

fn resident_entry_age_bounds<I>(current_tick: u64, entry_ticks: I) -> (u64, u64)
where
    I: Iterator<Item = u64>,
{
    let mut oldest_age = 0_u64;
    let mut newest_age = u64::MAX;
    let mut saw_entry = false;
    for last_access_tick in entry_ticks {
        saw_entry = true;
        let age = current_tick.saturating_sub(last_access_tick);
        oldest_age = oldest_age.max(age);
        newest_age = newest_age.min(age);
    }
    if saw_entry {
        (oldest_age, newest_age)
    } else {
        (0, 0)
    }
}

fn estimate_search_hit_bytes(hit: &SearchHit) -> usize {
    hit.index
        .len()
        .saturating_add(hit.metadata.id.len())
        .saturating_add(std::mem::size_of::<f32>())
        .saturating_add(estimate_value_bytes(&hit.source))
}

fn estimate_value_bytes(value: &Value) -> usize {
    match value {
        Value::Null => 0,
        Value::Bool(_) => 1,
        Value::Number(_) => 8,
        Value::String(text) => text.len(),
        Value::Array(values) => values.iter().map(estimate_value_bytes).sum(),
        Value::Object(entries) => entries
            .iter()
            .map(|(key, value)| key.len().saturating_add(estimate_value_bytes(value)))
            .sum(),
    }
}

fn aggregation_field_names(aggregations: &AggregationMap) -> Vec<String> {
    let mut fields = Vec::new();
    for aggregation in aggregations.values() {
        collect_aggregation_field_names(aggregation, &mut fields);
    }
    fields
}

fn collect_aggregation_field_names(aggregation: &Aggregation, fields: &mut Vec<String>) {
    match aggregation {
        Aggregation::Terms(terms) => fields.push(terms.field.clone()),
        Aggregation::Metric(metric) => fields.push(metric.field.clone()),
        Aggregation::Composite(composite) => {
            for source in &composite.sources {
                fields.push(source.field.clone());
            }
        }
        Aggregation::SignificantTerms(significant_terms) => {
            fields.push(significant_terms.field.clone());
        }
        Aggregation::GeoBounds(geo_bounds) => fields.push(geo_bounds.field.clone()),
        Aggregation::Filter(_)
        | Aggregation::Filters(_)
        | Aggregation::TopHits(_)
        | Aggregation::Pipeline(_)
        | Aggregation::ScriptedMetric(_)
        | Aggregation::Plugin(_) => {}
    }
}

fn knn_queries<'a>(query: &'a Query) -> Vec<&'a KnnQuery> {
    let mut queries = Vec::new();
    collect_knn_queries(query, &mut queries);
    queries
}

fn collect_knn_queries<'a>(query: &'a Query, queries: &mut Vec<&'a KnnQuery>) {
    match query {
        Query::Knn(knn_query) => {
            queries.push(knn_query);
            if let Some(filter) = knn_query.filter.as_deref() {
                collect_knn_queries(filter, queries);
            }
        }
        Query::Bool { clauses } => {
            for clause in clauses
                .must
                .iter()
                .chain(clauses.should.iter())
                .chain(clauses.filter.iter())
                .chain(clauses.must_not.iter())
            {
                collect_knn_queries(clause, queries);
            }
        }
        _ => {}
    }
}

fn read_u32_setting(settings: &Value, name: &str, default_value: u32) -> EngineResult<u32> {
    let Some(value) = settings
        .get("index")
        .and_then(|index| index.get(name))
        .or_else(|| settings.get(name))
    else {
        return Ok(default_value);
    };

    if let Some(number) = value.as_u64() {
        return u32::try_from(number)
            .map_err(|_| invalid_request(format!("setting [{name}] is too large")));
    }

    if let Some(text) = value.as_str() {
        return text
            .parse::<u32>()
            .map_err(|_| invalid_request(format!("setting [{name}] must be an unsigned integer")));
    }

    Err(invalid_request(format!(
        "setting [{name}] must be an unsigned integer"
    )))
}

fn read_field_mappings(mappings: &Value) -> EngineResult<Vec<TantivyFieldMapping>> {
    let Some(properties) = mappings.get("properties") else {
        return Ok(Vec::new());
    };
    let Some(properties) = properties.as_object() else {
        return Err(invalid_request("mappings.properties must be an object"));
    };

    let mut fields = Vec::with_capacity(properties.len());
    for (name, mapping) in properties {
        if !mapping.is_object() {
            return Err(invalid_request(format!(
                "mapping for field [{name}] must be an object"
            )));
        }
        let field_type = mapping
            .get("type")
            .and_then(Value::as_str)
            .unwrap_or("object");
        if field_type == KNN_VECTOR_FIELD_TYPE {
            let knn_vector = parse_knn_vector_mapping(mapping).map_err(|error| {
                invalid_request(format!(
                    "invalid knn_vector mapping for field [{name}]: {error}"
                ))
            })?;
            fields.push(TantivyFieldMapping {
                name: name.clone(),
                field_type: TantivyFieldType::KnnVector,
                indexed: mapping
                    .get("index")
                    .and_then(Value::as_bool)
                    .unwrap_or(true),
                stored: knn_vector.stored,
                fast: knn_vector.doc_values,
                knn_vector: Some(knn_vector),
            });
            continue;
        }
        fields.push(TantivyFieldMapping {
            name: name.clone(),
            field_type: map_field_type(name, field_type)?,
            indexed: mapping
                .get("index")
                .and_then(Value::as_bool)
                .unwrap_or(true),
            stored: mapping
                .get("store")
                .and_then(Value::as_bool)
                .unwrap_or(false),
            fast: mapping
                .get("doc_values")
                .and_then(Value::as_bool)
                .unwrap_or(matches!(
                    field_type,
                    "keyword" | "integer" | "long" | "short" | "byte" | "float" | "double" | "date"
                )),
            knn_vector: None,
        });
    }
    Ok(fields)
}

fn read_dynamic_mapping(mappings: &Value) -> EngineResult<bool> {
    match mappings.get("dynamic") {
        None => Ok(true),
        Some(Value::Bool(value)) => Ok(*value),
        Some(Value::String(value)) if value == "true" => Ok(true),
        Some(Value::String(value)) if value == "false" || value == "strict" => Ok(false),
        Some(_) => Err(invalid_request(
            "mappings.dynamic must be a boolean or one of [true, false, strict]",
        )),
    }
}

fn map_field_type(name: &str, field_type: &str) -> EngineResult<TantivyFieldType> {
    match field_type {
        "text" => Ok(TantivyFieldType::Text),
        "keyword" => Ok(TantivyFieldType::Keyword),
        "byte" | "short" | "integer" | "long" => Ok(TantivyFieldType::I64),
        "float" | "double" => Ok(TantivyFieldType::F64),
        "boolean" => Ok(TantivyFieldType::Bool),
        "date" => Ok(TantivyFieldType::Date),
        "geo_point" => Ok(TantivyFieldType::GeoPoint),
        _ => Err(invalid_request(format!(
            "unsupported OpenSearch field type [{field_type}] for field [{name}]"
        ))),
    }
}

fn invalid_request(reason: impl Into<String>) -> os_engine::EngineError {
    os_engine::EngineError::InvalidRequest {
        reason: reason.into(),
    }
}

fn parse_search_aggregation_map(value: &Value) -> EngineResult<AggregationMap> {
    if value.as_object().is_some_and(|object| object.is_empty()) {
        return Ok(AggregationMap::new());
    }

    parse_aggregation_map(value)
        .map_err(|error| invalid_request(format!("failed to parse aggregations: {error}")))
}

fn document_matches_query(query: &Query, id: &str, source: &Value) -> bool {
    match query {
        Query::MatchAll => true,
        Query::MatchNone => false,
        Query::Term { field, value } => source.get(field) == Some(value),
        Query::Terms { field, values } => source
            .get(field)
            .is_some_and(|value| matches_terms_query(value, values)),
        Query::Match { field, query } => matches_match_query(source.get(field), query),
        Query::Range { field, bounds } => source
            .get(field)
            .is_some_and(|value| matches_range_query(value, bounds)),
        Query::Exists { field } => source.get(field).is_some_and(|value| !value.is_null()),
        Query::Ids { values } => values.iter().any(|value| value == id),
        Query::Prefix {
            field,
            value,
            case_insensitive,
        } => source
            .get(field)
            .is_some_and(|field_value| matches_prefix_query(field_value, value, *case_insensitive)),
        Query::Wildcard {
            field,
            value,
            case_insensitive,
        } => source.get(field).is_some_and(|field_value| {
            matches_wildcard_query(field_value, value, *case_insensitive)
        }),
        Query::Knn(_) => false,
        Query::Bool { clauses } => matches_bool_query(clauses, id, source),
    }
}

fn query_uses_vector_scores(query: &Query) -> bool {
    match query {
        Query::Knn(_) => true,
        Query::Bool { clauses } => clauses
            .must
            .iter()
            .chain(clauses.should.iter())
            .chain(clauses.filter.iter())
            .chain(clauses.must_not.iter())
            .any(query_uses_vector_scores),
        _ => false,
    }
}

fn matches_terms_query(field_value: &Value, values: &[Value]) -> bool {
    match field_value {
        Value::Array(items) => items
            .iter()
            .any(|item| values.iter().any(|value| item == value)),
        _ => values.iter().any(|value| field_value == value),
    }
}

fn matches_match_query(field_value: Option<&Value>, query: &Value) -> bool {
    let Some(field_value) = field_value else {
        return false;
    };

    match (field_value, query) {
        (Value::String(field_value), Value::String(query)) => field_value.contains(query),
        _ => field_value == query,
    }
}

fn matches_range_query(value: &Value, bounds: &RangeBounds) -> bool {
    bound_matches(value, bounds.gt.as_ref(), |ordering| ordering.is_gt())
        && bound_matches(value, bounds.gte.as_ref(), |ordering| ordering.is_ge())
        && bound_matches(value, bounds.lt.as_ref(), |ordering| ordering.is_lt())
        && bound_matches(value, bounds.lte.as_ref(), |ordering| ordering.is_le())
}

fn bound_matches(
    value: &Value,
    bound: Option<&Value>,
    predicate: impl FnOnce(std::cmp::Ordering) -> bool,
) -> bool {
    let Some(bound) = bound else {
        return true;
    };

    compare_values(value, bound).is_some_and(predicate)
}

fn compare_values(left: &Value, right: &Value) -> Option<std::cmp::Ordering> {
    match (left, right) {
        (Value::Number(left), Value::Number(right)) => left
            .as_f64()
            .zip(right.as_f64())
            .and_then(|(left, right)| left.partial_cmp(&right)),
        (Value::String(left), Value::String(right)) => Some(left.cmp(right)),
        _ => None,
    }
}

fn matches_prefix_query(field_value: &Value, prefix: &str, case_insensitive: bool) -> bool {
    let Some(field_value) = field_value.as_str() else {
        return false;
    };

    if case_insensitive {
        field_value
            .to_lowercase()
            .starts_with(&prefix.to_lowercase())
    } else {
        field_value.starts_with(prefix)
    }
}

fn matches_wildcard_query(field_value: &Value, pattern: &str, case_insensitive: bool) -> bool {
    let Some(field_value) = field_value.as_str() else {
        return false;
    };

    if case_insensitive {
        wildcard_matches(&pattern.to_lowercase(), &field_value.to_lowercase())
    } else {
        wildcard_matches(pattern, field_value)
    }
}

fn wildcard_matches(pattern: &str, value: &str) -> bool {
    let pattern = pattern.as_bytes();
    let value = value.as_bytes();
    let (mut pattern_index, mut value_index) = (0, 0);
    let mut star_index = None;
    let mut star_value_index = 0;

    while value_index < value.len() {
        if pattern_index < pattern.len()
            && (pattern[pattern_index] == b'?' || pattern[pattern_index] == value[value_index])
        {
            pattern_index += 1;
            value_index += 1;
        } else if pattern_index < pattern.len() && pattern[pattern_index] == b'*' {
            star_index = Some(pattern_index);
            pattern_index += 1;
            star_value_index = value_index;
        } else if let Some(star) = star_index {
            pattern_index = star + 1;
            star_value_index += 1;
            value_index = star_value_index;
        } else {
            return false;
        }
    }

    while pattern_index < pattern.len() && pattern[pattern_index] == b'*' {
        pattern_index += 1;
    }

    pattern_index == pattern.len()
}

fn matches_bool_query(clauses: &BoolQuery, id: &str, source: &Value) -> bool {
    if !clauses
        .must
        .iter()
        .all(|query| document_matches_query(query, id, source))
    {
        return false;
    }
    if !clauses
        .filter
        .iter()
        .all(|query| document_matches_query(query, id, source))
    {
        return false;
    }
    if clauses
        .must_not
        .iter()
        .any(|query| document_matches_query(query, id, source))
    {
        return false;
    }

    let default_minimum_should_match = usize::from(
        !clauses.should.is_empty() && clauses.must.is_empty() && clauses.filter.is_empty(),
    );
    let minimum_should_match = clauses
        .minimum_should_match
        .map(|value| value as usize)
        .unwrap_or(default_minimum_should_match);
    let matching_should_clauses = clauses
        .should
        .iter()
        .filter(|query| document_matches_query(query, id, source))
        .count();

    matching_should_clauses >= minimum_should_match
}

fn sort_hits(hits: &mut [SearchHit], sort_specs: &[SortSpec]) {
    if sort_specs.is_empty() {
        return;
    }

    hits.sort_by(|left, right| {
        for sort_spec in sort_specs {
            let ordering = compare_hits_by_sort(left, right, sort_spec);
            if !ordering.is_eq() {
                return match sort_spec.order {
                    SortOrder::Asc => ordering,
                    SortOrder::Desc => ordering.reverse(),
                };
            }
        }

        std::cmp::Ordering::Equal
    });
}

fn compare_hits_by_sort(
    left: &SearchHit,
    right: &SearchHit,
    sort_spec: &SortSpec,
) -> std::cmp::Ordering {
    match sort_spec.field.as_str() {
        "_id" => left.metadata.id.cmp(&right.metadata.id),
        "_score" => left
            .score
            .partial_cmp(&right.score)
            .unwrap_or(std::cmp::Ordering::Equal),
        field => compare_optional_sort_values(left.source.get(field), right.source.get(field)),
    }
}

fn compare_optional_sort_values(left: Option<&Value>, right: Option<&Value>) -> std::cmp::Ordering {
    match (left, right) {
        (Some(left), Some(right)) => {
            compare_values(left, right).unwrap_or(std::cmp::Ordering::Equal)
        }
        (Some(_), None) => std::cmp::Ordering::Less,
        (None, Some(_)) => std::cmp::Ordering::Greater,
        (None, None) => std::cmp::Ordering::Equal,
    }
}

fn collect_aggregations(
    hits: &[SearchHit],
    all_hits: &[SearchHit],
    aggregation_map: &AggregationMap,
) -> Value {
    let mut aggregations = serde_json::Map::new();

    for (name, aggregation) in aggregation_map {
        match aggregation {
            Aggregation::Terms(terms) => {
                aggregations.insert(name.clone(), collect_terms_aggregation(hits, terms));
            }
            Aggregation::Metric(metric) => {
                aggregations.insert(name.clone(), collect_metric_aggregation(hits, metric));
            }
            Aggregation::Filter(filter) => {
                aggregations.insert(name.clone(), collect_filter_aggregation(hits, filter));
            }
            Aggregation::Filters(filters) => {
                aggregations.insert(name.clone(), collect_filters_aggregation(hits, filters));
            }
            Aggregation::TopHits(top_hits) => {
                aggregations.insert(name.clone(), collect_top_hits_aggregation(hits, top_hits));
            }
            Aggregation::Composite(composite) => {
                aggregations.insert(name.clone(), collect_composite_aggregation(hits, composite));
            }
            Aggregation::SignificantTerms(significant_terms) => {
                aggregations.insert(
                    name.clone(),
                    collect_significant_terms_aggregation(hits, all_hits, significant_terms),
                );
            }
            Aggregation::GeoBounds(geo_bounds) => {
                aggregations.insert(
                    name.clone(),
                    collect_geo_bounds_aggregation(hits, geo_bounds),
                );
            }
            Aggregation::ScriptedMetric(scripted_metric) => {
                aggregations.insert(
                    name.clone(),
                    collect_scripted_metric_aggregation(scripted_metric),
                );
            }
            Aggregation::Plugin(plugin) => {
                aggregations.insert(name.clone(), collect_plugin_aggregation(plugin));
            }
            Aggregation::Pipeline(_) => {}
        }
    }

    for (name, aggregation) in aggregation_map {
        if let Aggregation::Pipeline(pipeline) = aggregation {
            aggregations.insert(
                name.clone(),
                collect_pipeline_aggregation(&aggregations, pipeline),
            );
        }
    }

    Value::Object(aggregations)
}

fn collect_scripted_metric_aggregation(
    scripted_metric: &os_query_dsl::ScriptedMetricAggregation,
) -> Value {
    serde_json::json!({
        "value": scripted_metric.value.clone()
    })
}

fn collect_plugin_aggregation(plugin: &os_query_dsl::PluginAggregation) -> Value {
    serde_json::json!({
        "value": Value::Null,
        "_plugin": plugin.name.clone(),
        "_type": plugin.kind.clone(),
        "params": plugin.params.clone()
    })
}

fn collect_pipeline_aggregation(
    aggregations: &serde_json::Map<String, Value>,
    pipeline: &os_query_dsl::PipelineAggregation,
) -> Value {
    match pipeline.kind {
        os_query_dsl::PipelineAggregationKind::SumBucket => {
            serde_json::json!({
                "value": sum_bucket_pipeline_value(aggregations, &pipeline.buckets_path)
            })
        }
    }
}

fn sum_bucket_pipeline_value(
    aggregations: &serde_json::Map<String, Value>,
    buckets_path: &str,
) -> Option<f64> {
    let bucket_aggregation = buckets_path
        .strip_suffix(">_count")
        .or_else(|| buckets_path.strip_suffix("._count"))?;
    let buckets = aggregations.get(bucket_aggregation)?.get("buckets")?;

    if let Some(buckets) = buckets.as_array() {
        return Some(
            buckets
                .iter()
                .filter_map(|bucket| bucket.get("doc_count").and_then(Value::as_f64))
                .sum(),
        );
    }

    let buckets = buckets.as_object()?;
    Some(
        buckets
            .values()
            .filter_map(|bucket| bucket.get("doc_count").and_then(Value::as_f64))
            .sum(),
    )
}

fn collect_geo_bounds_aggregation(
    hits: &[SearchHit],
    geo_bounds: &os_query_dsl::GeoBoundsAggregation,
) -> Value {
    let mut min_lat = f64::INFINITY;
    let mut max_lat = f64::NEG_INFINITY;
    let mut min_lon = f64::INFINITY;
    let mut max_lon = f64::NEG_INFINITY;
    let mut point_count = 0_u64;

    for hit in hits {
        let Some((lat, lon)) = geo_point_source_value(&hit.source, &geo_bounds.field) else {
            continue;
        };
        min_lat = min_lat.min(lat);
        max_lat = max_lat.max(lat);
        min_lon = min_lon.min(lon);
        max_lon = max_lon.max(lon);
        point_count += 1;
    }

    if point_count == 0 {
        return serde_json::json!({
            "bounds": {
                "top_left": Value::Null,
                "bottom_right": Value::Null
            }
        });
    }

    serde_json::json!({
        "bounds": {
            "top_left": {
                "lat": max_lat,
                "lon": min_lon
            },
            "bottom_right": {
                "lat": min_lat,
                "lon": max_lon
            }
        }
    })
}

fn collect_significant_terms_aggregation(
    hits: &[SearchHit],
    all_hits: &[SearchHit],
    significant_terms: &os_query_dsl::SignificantTermsAggregation,
) -> Value {
    let mut buckets = BTreeMap::<String, (Value, u64)>::new();
    let mut background_counts = BTreeMap::<String, u64>::new();

    for hit in all_hits {
        let Some(value) = hit
            .source
            .get(&significant_terms.field)
            .filter(|value| is_scalar_value(value))
        else {
            continue;
        };
        *background_counts.entry(bucket_sort_key(value)).or_insert(0) += 1;
    }

    for hit in hits {
        let Some(value) = hit
            .source
            .get(&significant_terms.field)
            .filter(|value| is_scalar_value(value))
        else {
            continue;
        };
        let bucket_key = bucket_sort_key(value);
        let (_, doc_count) = buckets
            .entry(bucket_key)
            .or_insert_with(|| (value.clone(), 0));
        *doc_count += 1;
    }

    let mut buckets = buckets.into_values().collect::<Vec<_>>();
    buckets.sort_by(|(left_key, left_count), (right_key, right_count)| {
        right_count
            .cmp(left_count)
            .then_with(|| bucket_sort_key(left_key).cmp(&bucket_sort_key(right_key)))
    });

    serde_json::json!({
        "doc_count": hits.len() as u64,
        "bg_count": all_hits.len() as u64,
        "buckets": buckets
            .into_iter()
            .take(significant_terms.size)
            .map(|(key, doc_count)| {
                let bg_count = background_counts
                    .get(&bucket_sort_key(&key))
                    .copied()
                    .unwrap_or(doc_count);
                serde_json::json!({
                    "key": key,
                    "doc_count": doc_count,
                    "bg_count": bg_count,
                    "score": doc_count as f64
                })
            })
            .collect::<Vec<_>>()
    })
}

fn collect_composite_aggregation(
    hits: &[SearchHit],
    composite: &os_query_dsl::CompositeAggregation,
) -> Value {
    let mut buckets = BTreeMap::<String, (Value, u64)>::new();

    for hit in hits {
        let Some(key) = composite_key(&hit.source, &composite.sources) else {
            continue;
        };
        let bucket_key = serde_json::to_string(&key).unwrap_or_else(|_| key.to_string());
        let (_, doc_count) = buckets.entry(bucket_key).or_insert_with(|| (key, 0));
        *doc_count += 1;
    }

    let bucket_values = buckets
        .into_values()
        .take(composite.size)
        .map(|(key, doc_count)| {
            serde_json::json!({
                "key": key,
                "doc_count": doc_count
            })
        })
        .collect::<Vec<_>>();

    let mut response = serde_json::Map::new();
    if let Some(after_key) = bucket_values.last().map(|bucket| bucket["key"].clone()) {
        response.insert("after_key".to_string(), after_key);
    }
    response.insert("buckets".to_string(), Value::Array(bucket_values));

    Value::Object(response)
}

fn composite_key(source: &Value, sources: &[os_query_dsl::CompositeTermsSource]) -> Option<Value> {
    let mut key = serde_json::Map::new();

    for terms_source in sources {
        let value = source
            .get(&terms_source.field)
            .filter(|value| is_scalar_value(value))?;
        key.insert(terms_source.name.clone(), value.clone());
    }

    Some(Value::Object(key))
}

fn collect_top_hits_aggregation(
    hits: &[SearchHit],
    top_hits: &os_query_dsl::TopHitsAggregation,
) -> Value {
    let selected_hits = hits
        .iter()
        .skip(top_hits.from)
        .take(top_hits.size)
        .cloned()
        .collect::<Vec<_>>();
    let max_score = selected_hits
        .iter()
        .map(|hit| hit.score)
        .reduce(f32::max)
        .map(Value::from)
        .unwrap_or(Value::Null);

    serde_json::json!({
        "hits": {
            "total": {
                "value": hits.len() as u64,
                "relation": "eq"
            },
            "max_score": max_score,
            "hits": selected_hits
                .iter()
                .map(SearchHit::to_opensearch_body)
                .collect::<Vec<_>>()
        }
    })
}

fn collect_filter_aggregation(
    hits: &[SearchHit],
    filter: &os_query_dsl::FilterAggregation,
) -> Value {
    serde_json::json!({
        "doc_count": count_matching_hits(hits, &filter.filter)
    })
}

fn collect_filters_aggregation(
    hits: &[SearchHit],
    filters: &os_query_dsl::FiltersAggregation,
) -> Value {
    let mut buckets = serde_json::Map::new();

    for (name, query) in &filters.filters {
        buckets.insert(
            name.clone(),
            serde_json::json!({
                "doc_count": count_matching_hits(hits, query)
            }),
        );
    }

    serde_json::json!({
        "buckets": buckets
    })
}

fn count_matching_hits(hits: &[SearchHit], query: &Query) -> u64 {
    hits.iter()
        .filter(|hit| document_matches_query(query, &hit.metadata.id, &hit.source))
        .count() as u64
}

fn collect_metric_aggregation(
    hits: &[SearchHit],
    metric: &os_query_dsl::MetricAggregation,
) -> Value {
    let values = hits
        .iter()
        .filter_map(|hit| numeric_source_value(&hit.source, &metric.field))
        .collect::<Vec<_>>();

    let value = match metric.kind {
        os_query_dsl::MetricAggregationKind::Min => values.iter().copied().reduce(f64::min),
        os_query_dsl::MetricAggregationKind::Max => values.iter().copied().reduce(f64::max),
        os_query_dsl::MetricAggregationKind::Sum => Some(values.iter().sum::<f64>()),
        os_query_dsl::MetricAggregationKind::Avg => {
            if values.is_empty() {
                None
            } else {
                Some(values.iter().sum::<f64>() / values.len() as f64)
            }
        }
        os_query_dsl::MetricAggregationKind::ValueCount => Some(values.len() as f64),
    };

    serde_json::json!({
        "value": value
    })
}

fn numeric_source_value(source: &Value, field: &str) -> Option<f64> {
    source.get(field).and_then(Value::as_f64)
}

fn geo_point_source_value(source: &Value, field: &str) -> Option<(f64, f64)> {
    let point = source.get(field)?.as_object()?;
    let lat = point.get("lat")?.as_f64()?;
    let lon = point.get("lon")?.as_f64()?;
    Some((lat, lon))
}

fn collect_terms_aggregation(hits: &[SearchHit], terms: &os_query_dsl::TermsAggregation) -> Value {
    let mut buckets = BTreeMap::<String, (Value, u64)>::new();

    for hit in hits {
        let Some(value) = hit
            .source
            .get(&terms.field)
            .filter(|value| is_scalar_value(value))
        else {
            continue;
        };
        let bucket_key = bucket_sort_key(value);
        let (_, doc_count) = buckets
            .entry(bucket_key)
            .or_insert_with(|| (value.clone(), 0));
        *doc_count += 1;
    }

    let mut buckets = buckets.into_values().collect::<Vec<_>>();
    buckets.sort_by(|(left_key, left_count), (right_key, right_count)| {
        right_count
            .cmp(left_count)
            .then_with(|| bucket_sort_key(left_key).cmp(&bucket_sort_key(right_key)))
    });

    serde_json::json!({
        "buckets": buckets
            .into_iter()
            .take(terms.size)
            .map(|(key, doc_count)| {
                serde_json::json!({
                    "key": key,
                    "doc_count": doc_count
                })
            })
            .collect::<Vec<_>>()
    })
}

fn is_scalar_value(value: &Value) -> bool {
    matches!(value, Value::String(_) | Value::Bool(_) | Value::Number(_))
}

fn bucket_sort_key(value: &Value) -> String {
    match value {
        Value::String(value) => format!("s:{value}"),
        Value::Bool(value) => format!("b:{value}"),
        Value::Number(value) => format!("n:{value}"),
        _ => String::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use os_engine::{
        shard_manifest_checksum, BulkWriteOperation, BulkWriteRequest, WriteOperationKind,
    };
    use std::time::{SystemTime, UNIX_EPOCH};

    #[test]
    fn maps_opensearch_settings_and_fields_to_tantivy_schema_spec() {
        let schema = map_opensearch_index_to_tantivy_schema(&CreateIndexRequest {
            index: "logs-000001".to_string(),
            settings: serde_json::json!({
                "index": {
                    "number_of_shards": "3",
                    "number_of_replicas": 0
                }
            }),
            mappings: serde_json::json!({
                "properties": {
                    "message": { "type": "text" },
                    "service": { "type": "keyword", "store": true },
                    "bytes": { "type": "long" },
                    "ratio": { "type": "double" },
                    "success": { "type": "boolean" },
                    "created_at": { "type": "date" }
                }
            }),
        })
        .unwrap();

        assert_eq!(schema.number_of_shards, 3);
        assert_eq!(schema.number_of_replicas, 0);
        assert!(schema.dynamic);
        assert_eq!(schema.fields.len(), 6);

        let bytes = field(&schema, "bytes");
        assert_eq!(bytes.field_type, TantivyFieldType::I64);
        assert!(bytes.fast);

        let message = field(&schema, "message");
        assert_eq!(message.field_type, TantivyFieldType::Text);
        assert!(!message.fast);

        let ratio = field(&schema, "ratio");
        assert_eq!(ratio.field_type, TantivyFieldType::F64);

        let service = field(&schema, "service");
        assert!(service.stored);
    }

    #[test]
    fn maps_knn_vector_mapping_to_tantivy_schema_spec() {
        let schema = map_opensearch_index_to_tantivy_schema(&CreateIndexRequest {
            index: "vectors".to_string(),
            settings: serde_json::json!({}),
            mappings: serde_json::json!({
                "properties": {
                    "embedding": {
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
                    }
                }
            }),
        })
        .unwrap();

        let embedding = field(&schema, "embedding");
        assert_eq!(embedding.field_type, TantivyFieldType::KnnVector);
        assert!(embedding.indexed);
        assert!(embedding.stored);
        assert!(!embedding.fast);

        let knn_vector = embedding.knn_vector.as_ref().unwrap();
        assert_eq!(knn_vector.dimension, 384);
        assert_eq!(
            knn_vector.data_type,
            os_plugin_knn::KnnVectorDataType::Float
        );
        assert_eq!(knn_vector.model_id.as_deref(), Some("mini-lm"));
        assert_eq!(
            knn_vector.method.as_ref().unwrap().engine.as_deref(),
            Some("faiss")
        );
        assert_eq!(
            knn_vector.method.as_ref().unwrap().parameters["ef_construction"],
            serde_json::json!(128)
        );
        assert_eq!(knn_vector.mode.as_deref(), Some("on_disk"));
        assert_eq!(knn_vector.compression_level.as_deref(), Some("16x"));
        assert_eq!(knn_vector.engine.as_deref(), Some("lucene"));
        assert_eq!(knn_vector.space_type.as_deref(), Some("cosinesimil"));
        assert_eq!(knn_vector.metadata["source"], serde_json::json!("minilm"));
    }

    #[test]
    fn engine_persists_vectors_and_searches_exact_and_hnsw() {
        let engine = TantivyEngine::default();
        let create = CreateIndexRequest {
            index: "vectors".to_string(),
            settings: serde_json::json!({}),
            mappings: serde_json::json!({
                "properties": {
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 3,
                        "space_type": "l2"
                    }
                }
            }),
        };
        engine.create_index(create).unwrap();
        for (id, embedding) in [
            ("a", serde_json::json!([1.0, 0.0, 0.0])),
            ("b", serde_json::json!([0.0, 1.0, 0.0])),
            ("c", serde_json::json!([0.8, 0.1, 0.0])),
        ] {
            engine
                .index_document(IndexDocumentRequest {
                    index: "vectors".to_string(),
                    id: id.to_string(),
                    source: serde_json::json!({
                        "embedding": embedding,
                        "name": id
                    }),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["vectors".to_string()],
            })
            .unwrap();

        let exact = engine
            .exact_vector_search("vectors", "embedding", &[1.0, 0.0, 0.0], 2)
            .unwrap();
        assert_eq!(
            exact.iter().map(|hit| hit.id.as_str()).collect::<Vec<_>>(),
            vec!["a", "c"]
        );
        assert_eq!(exact[0].score, -0.0);

        let graph = engine
            .hnsw_index_snapshot("vectors", "embedding", 2)
            .unwrap();
        assert_eq!(graph.field, "embedding");
        assert_eq!(graph.dimension, 3);
        assert_eq!(graph.nodes.len(), 3);
        assert!(graph
            .nodes
            .iter()
            .any(|node| node.id == "a" && node.neighbors.contains(&"c".to_string())));

        let hnsw = engine
            .hnsw_vector_search("vectors", "embedding", &[1.0, 0.0, 0.0], 2, 8)
            .unwrap();
        assert_eq!(
            hnsw.iter().map(|hit| hit.id.as_str()).collect::<Vec<_>>(),
            vec!["a", "c"]
        );

        let segments = engine.vector_segment_metadata("vectors").unwrap();
        assert_eq!(segments.len(), 1);
        assert_eq!(segments[0].field, "embedding");
        assert_eq!(segments[0].dimension, 3);
        assert_eq!(segments[0].vector_count, 3);
        assert_eq!(
            segments[0].ann_graph.as_deref(),
            Some("steelsearch-native-hnsw")
        );

        let shard_path = unique_temp_path("os-tantivy-vector-recovery");
        let manifest = engine.persist_shard_state("vectors", &shard_path).unwrap();
        assert_eq!(manifest.vector_segments, segments);

        let recovered = TantivyEngine::default();
        recovered
            .recover_index_from_manifest(
                "vectors",
                engine.index_schema("vectors").unwrap(),
                &shard_path,
            )
            .unwrap();
        let recovered_hits = recovered
            .exact_vector_search("vectors", "embedding", &[1.0, 0.0, 0.0], 2)
            .unwrap();
        assert_eq!(
            recovered_hits
                .iter()
                .map(|hit| hit.id.as_str())
                .collect::<Vec<_>>(),
            vec!["a", "c"]
        );

        let _ = std::fs::remove_dir_all(shard_path);
    }

    #[test]
    fn engine_executes_knn_query_with_filter_and_vector_scores() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "vectors".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 3,
                            "space_type": "l2"
                        },
                        "tenant": { "type": "keyword" }
                    }
                }),
            })
            .unwrap();

        for (id, tenant, embedding) in [
            ("a", "one", serde_json::json!([1.0, 0.0, 0.0])),
            ("b", "two", serde_json::json!([0.95, 0.0, 0.0])),
            ("c", "one", serde_json::json!([0.0, 1.0, 0.0])),
        ] {
            engine
                .index_document(IndexDocumentRequest {
                    index: "vectors".to_string(),
                    id: id.to_string(),
                    source: serde_json::json!({
                        "tenant": tenant,
                        "embedding": embedding
                    }),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["vectors".to_string()],
            })
            .unwrap();

        let response = engine
            .search(SearchRequest {
                indices: vec!["vectors".to_string()],
                query: serde_json::json!({
                    "knn": {
                        "embedding": {
                            "vector": [1.0, 0.0, 0.0],
                            "k": 2,
                            "filter": { "term": { "tenant": "one" } },
                            "max_distance": 2.0,
                            "method_parameters": { "ef_search": 8 },
                            "rescore": { "oversample_factor": 2.0 }
                        }
                    }
                }),
                aggregations: serde_json::json!({}),
                sort: Vec::new(),
                from: 0,
                size: 10,
            })
            .unwrap();

        assert_eq!(response.total_hits, 2);
        assert_eq!(response.hits[0].metadata.id, "a");
        assert_eq!(response.hits[1].metadata.id, "c");
        assert!(response.hits[0].score > response.hits[1].score);
    }

    #[test]
    fn vector_correctness_matches_exact_hnsw_filter_and_hybrid_rankings() {
        for (space_type, query_vector) in [
            ("l2", serde_json::json!([1.0, 0.0, 0.0])),
            ("cosinesimil", serde_json::json!([1.0, 0.0, 0.0])),
            ("innerproduct", serde_json::json!([1.0, 0.0, 0.0])),
        ] {
            let index = format!("vectors-{space_type}");
            let engine = TantivyEngine::default();
            engine
                .create_index(CreateIndexRequest {
                    index: index.clone(),
                    settings: serde_json::json!({}),
                    mappings: serde_json::json!({
                        "properties": {
                            "embedding": {
                                "type": "knn_vector",
                                "dimension": 3,
                                "space_type": space_type
                            },
                            "tenant": { "type": "keyword" },
                            "body": { "type": "text" }
                        }
                    }),
                })
                .unwrap();

            for (id, tenant, body, embedding) in [
                (
                    "a",
                    "fruit",
                    "fresh apple vector",
                    serde_json::json!([1.0, 0.0, 0.0]),
                ),
                (
                    "b",
                    "fruit",
                    "green apple vector",
                    serde_json::json!([0.9, 0.1, 0.0]),
                ),
                (
                    "c",
                    "vehicle",
                    "blue car vector",
                    serde_json::json!([0.0, 1.0, 0.0]),
                ),
                (
                    "d",
                    "fruit",
                    "distant pear vector",
                    serde_json::json!([0.4, 0.6, 0.0]),
                ),
            ] {
                engine
                    .index_document(IndexDocumentRequest {
                        index: index.clone(),
                        id: id.to_string(),
                        source: serde_json::json!({
                            "tenant": tenant,
                            "body": body,
                            "embedding": embedding
                        }),
                    })
                    .unwrap();
            }
            engine
                .refresh(RefreshRequest {
                    indices: vec![index.clone()],
                })
                .unwrap();

            let exact = engine
                .exact_vector_search(&index, "embedding", &[1.0, 0.0, 0.0], 3)
                .unwrap();
            assert_eq!(hit_ids(&exact), vec!["a", "b", "d"], "{space_type} exact");

            let hnsw = engine
                .hnsw_vector_search(&index, "embedding", &[1.0, 0.0, 0.0], 3, 8)
                .unwrap();
            assert_eq!(hit_ids(&hnsw), vec!["a", "b", "d"], "{space_type} hnsw");

            let filtered = engine
                .search(SearchRequest {
                    indices: vec![index.clone()],
                    query: serde_json::json!({
                        "knn": {
                            "embedding": {
                                "vector": query_vector,
                                "k": 3,
                                "filter": {
                                    "term": {
                                        "tenant": "fruit"
                                    }
                                }
                            }
                        }
                    }),
                    aggregations: serde_json::json!({}),
                    sort: Vec::new(),
                    from: 0,
                    size: 10,
                })
                .unwrap();
            assert_eq!(
                search_hit_ids(&filtered.hits),
                vec!["a", "b", "d"],
                "{space_type} filtered query"
            );

            let hybrid = engine
                .search(SearchRequest {
                    indices: vec![index.clone()],
                    query: serde_json::json!({
                        "bool": {
                            "must": [
                                {
                                    "match": {
                                        "body": "apple"
                                    }
                                }
                            ],
                            "should": [
                                {
                                    "knn": {
                                        "embedding": {
                                            "vector": [1.0, 0.0, 0.0],
                                            "k": 3
                                        }
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    }),
                    aggregations: serde_json::json!({}),
                    sort: Vec::new(),
                    from: 0,
                    size: 10,
                })
                .unwrap();
            assert_eq!(
                search_hit_ids(&hybrid.hits),
                vec!["a", "b"],
                "{space_type} hybrid query"
            );
        }
    }

    #[test]
    fn maps_geo_point_mapping_for_source_backed_geo_aggregations() {
        let schema = map_opensearch_index_to_tantivy_schema(&CreateIndexRequest {
            index: "places".to_string(),
            settings: serde_json::json!({}),
            mappings: serde_json::json!({
                "properties": {
                    "location": { "type": "geo_point" }
                }
            }),
        })
        .unwrap();

        let location = field(&schema, "location");
        assert_eq!(location.field_type, TantivyFieldType::GeoPoint);
        assert!(location.indexed);
        assert!(!location.fast);
        assert!(!location.stored);
    }

    #[test]
    fn engine_rejects_unsupported_knn_execution_options() {
        let engine = TantivyEngine::default();
        for (index, mapping, expected) in [
            (
                "vectors-byte",
                serde_json::json!({"data_type": "byte"}),
                "data_type [byte] is not supported",
            ),
            (
                "vectors-binary",
                serde_json::json!({"data_type": "binary"}),
                "data_type [binary] is not supported",
            ),
            (
                "vectors-space",
                serde_json::json!({"space_type": "hamming"}),
                "unsupported knn_vector space_type [hamming]",
            ),
            (
                "vectors-engine",
                serde_json::json!({"engine": "faiss"}),
                "unsupported knn_vector engine [faiss]",
            ),
            (
                "vectors-method-engine",
                serde_json::json!({"method": {"name": "hnsw", "engine": "nmslib"}}),
                "unsupported knn_vector engine [nmslib]",
            ),
            (
                "vectors-method-name",
                serde_json::json!({"method": {"name": "ivf"}}),
                "unsupported knn_vector method [ivf]",
            ),
            (
                "vectors-method-params",
                serde_json::json!({"method": {"name": "hnsw", "parameters": {"m": 16}}}),
                "unsupported knn_vector method parameters",
            ),
            (
                "vectors-mode",
                serde_json::json!({"mode": "on_disk"}),
                "unsupported knn_vector mode [on_disk]",
            ),
            (
                "vectors-compression",
                serde_json::json!({"compression_level": "16x"}),
                "unsupported knn_vector compression_level [16x]",
            ),
        ] {
            let mut embedding = serde_json::json!({
                "type": "knn_vector",
                "dimension": 3,
                "space_type": "l2"
            });
            if let (Some(base), Some(overrides)) = (embedding.as_object_mut(), mapping.as_object())
            {
                for (key, value) in overrides {
                    base.insert(key.clone(), value.clone());
                }
            }
            engine
                .create_index(CreateIndexRequest {
                    index: index.to_string(),
                    settings: serde_json::json!({}),
                    mappings: serde_json::json!({
                        "properties": {
                            "embedding": embedding
                        }
                    }),
                })
                .unwrap();

            let error = engine
                .exact_vector_search(index, "embedding", &[1.0, 0.0, 0.0], 1)
                .unwrap_err()
                .to_string();
            assert!(
                error.contains(expected),
                "expected [{expected}] in error [{error}]"
            );
        }
    }

    #[test]
    fn engine_retries_writes_after_dynamic_mapping_updates() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({}),
            })
            .unwrap();

        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({
                    "message": "hello",
                    "bytes": 42,
                    "success": true
                }),
            })
            .unwrap();
        engine
            .update_document(UpdateDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                doc: serde_json::json!({ "ratio": 1.5 }),
                doc_as_upsert: false,
            })
            .unwrap();

        let schema = engine.index_schema("logs-000001").unwrap();

        assert_eq!(field(&schema, "message").field_type, TantivyFieldType::Text);
        assert_eq!(field(&schema, "bytes").field_type, TantivyFieldType::I64);
        assert_eq!(field(&schema, "success").field_type, TantivyFieldType::Bool);
        assert_eq!(field(&schema, "ratio").field_type, TantivyFieldType::F64);
    }

    #[test]
    fn engine_rejects_unknown_fields_when_dynamic_mapping_is_disabled() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "dynamic": false,
                    "properties": {
                        "message": { "type": "text" }
                    }
                }),
            })
            .unwrap();

        let error = engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({
                    "message": "hello",
                    "bytes": 42
                }),
            })
            .unwrap_err();

        assert_eq!(error.status_code(), 400);
        assert_eq!(error.opensearch_error_type(), "illegal_argument_exception");
        assert!(error
            .opensearch_reason()
            .contains("dynamic mapping is disabled"));
    }

    #[test]
    fn engine_persists_source_and_document_metadata() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "message": { "type": "text" }
                    }
                }),
            })
            .unwrap();

        let created = engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({ "message": "hello" }),
            })
            .unwrap();
        let updated = engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({ "message": "updated" }),
            })
            .unwrap();
        let fetched = engine
            .get_document(GetDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
            })
            .unwrap()
            .unwrap();

        assert_eq!(created.result, WriteResult::Created);
        assert_eq!(created.metadata.version, 1);
        assert_eq!(created.metadata.seq_no, 0);
        assert_eq!(updated.result, WriteResult::Updated);
        assert_eq!(updated.metadata.version, 2);
        assert_eq!(updated.metadata.seq_no, 1);
        assert_eq!(updated.metadata.primary_term, 1);
        assert_eq!(fetched.metadata, updated.metadata);
        assert_eq!(fetched.source["message"], "updated");
    }

    #[test]
    fn engine_separates_primary_assignment_from_replica_replay() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "message": { "type": "text" }
                    }
                }),
            })
            .unwrap();

        let primary = engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "primary".to_string(),
                source: serde_json::json!({ "message": "primary" }),
            })
            .unwrap();
        let replayed = engine
            .replay_document(ReplayDocumentRequest {
                index: "logs-000001".to_string(),
                metadata: DocumentMetadata {
                    id: "replica".to_string(),
                    version: 9,
                    seq_no: 7,
                    primary_term: 4,
                },
                coordination: WriteCoordinationMetadata {
                    translog_location: Some(TranslogLocation {
                        generation: 3,
                        offset: 700,
                        size: 33,
                    }),
                    global_checkpoint: 6,
                    local_checkpoint: 7,
                    retention_leases: Vec::new(),
                    noop: true,
                },
                source: serde_json::json!({ "message": "replica" }),
            })
            .unwrap();
        let after_replay = engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "after-replay".to_string(),
                source: serde_json::json!({ "message": "after replay" }),
            })
            .unwrap();

        assert_eq!(primary.metadata.seq_no, 0);
        assert_eq!(primary.metadata.primary_term, 1);
        assert_eq!(primary.coordination.global_checkpoint, 0);
        assert_eq!(primary.coordination.local_checkpoint, 0);
        assert!(!primary.coordination.noop);
        assert_eq!(replayed.result, WriteResult::Created);
        assert_eq!(replayed.metadata.version, 9);
        assert_eq!(replayed.metadata.seq_no, 7);
        assert_eq!(replayed.metadata.primary_term, 4);
        assert_eq!(
            replayed.coordination.translog_location,
            Some(TranslogLocation {
                generation: 3,
                offset: 700,
                size: 33,
            })
        );
        assert_eq!(replayed.coordination.global_checkpoint, 6);
        assert_eq!(replayed.coordination.local_checkpoint, 7);
        assert!(replayed.coordination.noop);
        assert_eq!(after_replay.metadata.seq_no, 8);
        assert_eq!(after_replay.metadata.primary_term, 4);
    }

    #[test]
    fn engine_deletes_documents_with_write_metadata() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "message": { "type": "text" }
                    }
                }),
            })
            .unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({ "message": "delete me" }),
            })
            .unwrap();

        let deleted = engine
            .delete_document(DeleteDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
            })
            .unwrap();
        let fetched = engine
            .get_document(GetDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
            })
            .unwrap();
        let next_write = engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "2".to_string(),
                source: serde_json::json!({ "message": "after delete" }),
            })
            .unwrap();

        assert_eq!(deleted.result, WriteResult::Deleted);
        assert_eq!(deleted.metadata.id, "1");
        assert_eq!(deleted.metadata.version, 2);
        assert_eq!(deleted.metadata.seq_no, 1);
        assert_eq!(deleted.coordination.local_checkpoint, 1);
        assert_eq!(deleted.coordination.global_checkpoint, 1);
        assert!(deleted.coordination.translog_location.is_some());
        assert!(fetched.is_none());
        assert_eq!(next_write.metadata.seq_no, 2);
    }

    #[test]
    fn engine_rejects_delete_for_missing_document() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({}),
            })
            .unwrap();

        let error = engine
            .delete_document(DeleteDocumentRequest {
                index: "logs-000001".to_string(),
                id: "missing".to_string(),
            })
            .unwrap_err();

        assert_eq!(error.status_code(), 404);
        assert_eq!(error.opensearch_error_type(), "document_missing_exception");
    }

    #[test]
    fn engine_updates_documents_by_merging_partial_source() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "message": { "type": "text" },
                        "level": { "type": "keyword" }
                    }
                }),
            })
            .unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({
                    "message": "hello",
                    "level": "info"
                }),
            })
            .unwrap();

        let updated = engine
            .update_document(UpdateDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                doc: serde_json::json!({ "level": "debug" }),
                doc_as_upsert: false,
            })
            .unwrap();
        let fetched = engine
            .get_document(GetDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
            })
            .unwrap()
            .unwrap();

        assert_eq!(updated.result, WriteResult::Updated);
        assert_eq!(updated.metadata.version, 2);
        assert_eq!(updated.metadata.seq_no, 1);
        assert_eq!(updated.coordination.local_checkpoint, 1);
        assert_eq!(fetched.source["message"], "hello");
        assert_eq!(fetched.source["level"], "debug");
    }

    #[test]
    fn engine_update_supports_doc_as_upsert_and_missing_errors() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({}),
            })
            .unwrap();

        let missing = engine
            .update_document(UpdateDocumentRequest {
                index: "logs-000001".to_string(),
                id: "missing".to_string(),
                doc: serde_json::json!({ "message": "missing" }),
                doc_as_upsert: false,
            })
            .unwrap_err();
        let upserted = engine
            .update_document(UpdateDocumentRequest {
                index: "logs-000001".to_string(),
                id: "upserted".to_string(),
                doc: serde_json::json!({ "message": "created" }),
                doc_as_upsert: true,
            })
            .unwrap();

        assert_eq!(missing.status_code(), 404);
        assert_eq!(
            missing.opensearch_error_type(),
            "document_missing_exception"
        );
        assert_eq!(upserted.result, WriteResult::Created);
        assert_eq!(upserted.metadata.version, 1);
        assert_eq!(upserted.metadata.seq_no, 0);
    }

    #[test]
    fn engine_applies_optimistic_concurrency_controls() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({}),
            })
            .unwrap();
        let created = engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({ "message": "created" }),
            })
            .unwrap();

        let updated = engine
            .update_document_with_control(ConditionalUpdateDocumentRequest {
                request: UpdateDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: "1".to_string(),
                    doc: serde_json::json!({ "message": "updated" }),
                    doc_as_upsert: false,
                },
                condition: WriteCondition {
                    if_seq_no: Some(created.metadata.seq_no),
                    if_primary_term: Some(created.metadata.primary_term),
                    version: None,
                    version_type: VersionType::Internal,
                },
            })
            .unwrap();
        let stale = engine
            .update_document_with_control(ConditionalUpdateDocumentRequest {
                request: UpdateDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: "1".to_string(),
                    doc: serde_json::json!({ "message": "stale" }),
                    doc_as_upsert: false,
                },
                condition: WriteCondition {
                    if_seq_no: Some(created.metadata.seq_no),
                    if_primary_term: Some(created.metadata.primary_term),
                    version: None,
                    version_type: VersionType::Internal,
                },
            })
            .unwrap_err();

        assert_eq!(updated.metadata.seq_no, 1);
        assert_eq!(updated.metadata.version, 2);
        assert_eq!(stale.status_code(), 409);
        assert_eq!(
            stale.opensearch_error_type(),
            "version_conflict_engine_exception"
        );
    }

    #[test]
    fn engine_applies_external_versioning_controls() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({}),
            })
            .unwrap();

        let created = engine
            .index_document_with_control(ConditionalIndexDocumentRequest {
                request: IndexDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: "1".to_string(),
                    source: serde_json::json!({ "message": "v10" }),
                },
                condition: WriteCondition {
                    version: Some(10),
                    version_type: VersionType::External,
                    ..WriteCondition::default()
                },
            })
            .unwrap();
        let stale = engine
            .index_document_with_control(ConditionalIndexDocumentRequest {
                request: IndexDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: "1".to_string(),
                    source: serde_json::json!({ "message": "v9" }),
                },
                condition: WriteCondition {
                    version: Some(9),
                    version_type: VersionType::External,
                    ..WriteCondition::default()
                },
            })
            .unwrap_err();
        let same_version = engine
            .index_document_with_control(ConditionalIndexDocumentRequest {
                request: IndexDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: "1".to_string(),
                    source: serde_json::json!({ "message": "v10 gte" }),
                },
                condition: WriteCondition {
                    version: Some(10),
                    version_type: VersionType::ExternalGte,
                    ..WriteCondition::default()
                },
            })
            .unwrap();

        assert_eq!(created.metadata.version, 10);
        assert_eq!(stale.status_code(), 409);
        assert_eq!(same_version.metadata.version, 10);
        assert_eq!(same_version.metadata.seq_no, 1);
    }

    #[test]
    fn engine_bulk_write_applies_items_in_order_and_reports_partial_failures() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "message": { "type": "text" }
                    }
                }),
            })
            .unwrap();

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
                    BulkWriteOperation::Delete(DeleteDocumentRequest {
                        index: "logs-000001".to_string(),
                        id: "missing".to_string(),
                    }),
                ],
            })
            .unwrap();
        let fetched = engine
            .get_document(GetDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
            })
            .unwrap();

        assert!(bulk.errors);
        assert_eq!(bulk.items.len(), 4);
        assert_eq!(bulk.items[0].operation, WriteOperationKind::Index);
        assert_eq!(bulk.items[0].status, 201);
        assert_eq!(bulk.items[0].metadata.as_ref().unwrap().seq_no, 0);
        assert_eq!(bulk.items[1].operation, WriteOperationKind::Update);
        assert_eq!(bulk.items[1].result, Some(WriteResult::Updated));
        assert_eq!(bulk.items[1].metadata.as_ref().unwrap().seq_no, 1);
        assert_eq!(bulk.items[2].operation, WriteOperationKind::Delete);
        assert_eq!(bulk.items[2].result, Some(WriteResult::Deleted));
        assert_eq!(bulk.items[2].metadata.as_ref().unwrap().seq_no, 2);
        assert_eq!(bulk.items[3].operation, WriteOperationKind::Delete);
        assert_eq!(bulk.items[3].status, 404);
        assert_eq!(
            bulk.items[3].error_type.as_deref(),
            Some("document_missing_exception")
        );
        assert!(fetched.is_none());
    }

    #[test]
    fn engine_rejects_stale_replica_replay() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "message": { "type": "text" }
                    }
                }),
            })
            .unwrap();
        engine
            .replay_document(ReplayDocumentRequest {
                index: "logs-000001".to_string(),
                metadata: DocumentMetadata {
                    id: "1".to_string(),
                    version: 2,
                    seq_no: 5,
                    primary_term: 2,
                },
                coordination: WriteCoordinationMetadata::default(),
                source: serde_json::json!({ "message": "newer" }),
            })
            .unwrap();

        let error = engine
            .replay_document(ReplayDocumentRequest {
                index: "logs-000001".to_string(),
                metadata: DocumentMetadata {
                    id: "1".to_string(),
                    version: 1,
                    seq_no: 4,
                    primary_term: 2,
                },
                coordination: WriteCoordinationMetadata::default(),
                source: serde_json::json!({ "message": "older" }),
            })
            .unwrap_err();

        assert_eq!(error.status_code(), 400);
        assert_eq!(error.opensearch_error_type(), "illegal_argument_exception");
        assert!(error.opensearch_reason().contains("older than existing"));
    }

    #[test]
    fn engine_persists_shard_manifest_for_index_state() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "message": { "type": "text" }
                    }
                }),
            })
            .unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({ "message": "hello" }),
            })
            .unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "2".to_string(),
                source: serde_json::json!({ "message": "world" }),
            })
            .unwrap();

        let shard_path = unique_temp_path("os-tantivy-manifest");
        let manifest = engine
            .persist_shard_manifest("logs-000001", &shard_path)
            .unwrap();
        let loaded = load_shard_manifest(&shard_path).unwrap();

        assert_eq!(loaded, manifest);
        assert_eq!(loaded.shard_id, 0);
        assert_eq!(loaded.primary_term, 1);
        assert_eq!(loaded.max_sequence_number, 1);
        assert_eq!(loaded.local_checkpoint, 1);
        assert_eq!(loaded.refreshed_sequence_number, -1);
        assert_eq!(loaded.committed_generation, 0);
        assert_eq!(loaded.translog_generation, 0);
        assert_ne!(loaded.schema_hash, 0);
        assert!(loaded.index_uuid.starts_with("steelsearch-"));
        assert!(loaded.allocation_id.starts_with("alloc-"));

        let _ = std::fs::remove_dir_all(shard_path);
    }

    #[test]
    fn engine_recovers_shard_identity_and_sequence_counters_from_manifest() {
        let engine = TantivyEngine::default();
        let create = CreateIndexRequest {
            index: "logs-000001".to_string(),
            settings: serde_json::json!({}),
            mappings: serde_json::json!({
                "properties": {
                    "message": { "type": "text" }
                }
            }),
        };
        let schema = map_opensearch_index_to_tantivy_schema(&create).unwrap();
        engine.create_index(create).unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({ "message": "hello" }),
            })
            .unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "2".to_string(),
                source: serde_json::json!({ "message": "world" }),
            })
            .unwrap();

        let shard_path = unique_temp_path("os-tantivy-recovery");
        let saved = engine
            .persist_shard_state("logs-000001", &shard_path)
            .unwrap();

        let recovered_engine = TantivyEngine::default();
        let recovered = recovered_engine
            .recover_index_from_manifest("logs-000001", schema, &shard_path)
            .unwrap();
        let write_after_recovery = recovered_engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "3".to_string(),
                source: serde_json::json!({ "message": "after recovery" }),
            })
            .unwrap();

        assert_eq!(recovered, saved);
        assert_eq!(write_after_recovery.metadata.seq_no, 2);
        assert_eq!(
            write_after_recovery.metadata.primary_term,
            saved.primary_term
        );
        assert_eq!(
            recovered_engine
                .shard_manifest("logs-000001")
                .unwrap()
                .index_uuid,
            saved.index_uuid
        );
        assert!(recovered_engine
            .get_document(GetDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
            })
            .unwrap()
            .is_some());

        let _ = std::fs::remove_dir_all(shard_path);
    }

    #[test]
    fn engine_replays_operations_and_recovers_refresh_visibility() {
        let engine = TantivyEngine::default();
        let create = CreateIndexRequest {
            index: "logs-000001".to_string(),
            settings: serde_json::json!({}),
            mappings: serde_json::json!({
                "properties": {
                    "message": { "type": "text" }
                }
            }),
        };
        let schema = map_opensearch_index_to_tantivy_schema(&create).unwrap();
        engine.create_index(create).unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "visible".to_string(),
                source: serde_json::json!({ "message": "visible" }),
            })
            .unwrap();
        engine
            .refresh(RefreshRequest {
                indices: vec!["logs-000001".to_string()],
            })
            .unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "not-visible-yet".to_string(),
                source: serde_json::json!({ "message": "not visible yet" }),
            })
            .unwrap();

        let shard_path = unique_temp_path("os-tantivy-replay-refresh");
        let saved = engine
            .persist_shard_state("logs-000001", &shard_path)
            .unwrap();
        let recovered_engine = TantivyEngine::default();
        recovered_engine
            .recover_index_from_manifest("logs-000001", schema, &shard_path)
            .unwrap();

        let visible_search = recovered_engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "match_all": {} }),
                aggregations: serde_json::json!({}),
                sort: Vec::new(),
                from: 0,
                size: 10,
            })
            .unwrap();
        let unrefreshed_get = recovered_engine
            .get_document(GetDocumentRequest {
                index: "logs-000001".to_string(),
                id: "not-visible-yet".to_string(),
            })
            .unwrap();

        assert_eq!(saved.max_sequence_number, 1);
        assert_eq!(saved.refreshed_sequence_number, 0);
        assert_eq!(visible_search.total_hits, 1);
        assert_eq!(visible_search.hits[0].metadata.id, "visible");
        assert!(unrefreshed_get.is_some());

        let _ = std::fs::remove_dir_all(shard_path);
    }

    #[test]
    fn engine_rejects_recovery_when_schema_hash_differs() {
        let engine = TantivyEngine::default();
        let create = CreateIndexRequest {
            index: "logs-000001".to_string(),
            settings: serde_json::json!({}),
            mappings: serde_json::json!({
                "properties": {
                    "message": { "type": "text" }
                }
            }),
        };
        engine.create_index(create).unwrap();
        let shard_path = unique_temp_path("os-tantivy-recovery-schema-mismatch");
        engine
            .persist_shard_manifest("logs-000001", &shard_path)
            .unwrap();

        let mismatched_schema = TantivyIndexSchema {
            number_of_shards: 1,
            number_of_replicas: 1,
            dynamic: true,
            fields: vec![TantivyFieldMapping {
                name: "different".to_string(),
                field_type: TantivyFieldType::Keyword,
                indexed: true,
                stored: false,
                fast: true,
                knn_vector: None,
            }],
        };
        let error = TantivyEngine::default()
            .recover_index_from_manifest("logs-000001", mismatched_schema, &shard_path)
            .unwrap_err();

        assert_eq!(error.status_code(), 400);
        assert_eq!(error.opensearch_error_type(), "illegal_argument_exception");

        let _ = std::fs::remove_dir_all(shard_path);
    }

    #[test]
    fn engine_rejects_recovery_with_corrupt_operation_log() {
        let engine = TantivyEngine::default();
        let create = CreateIndexRequest {
            index: "logs-000001".to_string(),
            settings: serde_json::json!({}),
            mappings: serde_json::json!({
                "properties": {
                    "message": { "type": "text" }
                }
            }),
        };
        let schema = map_opensearch_index_to_tantivy_schema(&create).unwrap();
        engine.create_index(create).unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({ "message": "hello" }),
            })
            .unwrap();
        let shard_path = unique_temp_path("os-tantivy-corrupt-operation-log");
        engine
            .persist_shard_state("logs-000001", &shard_path)
            .unwrap();
        std::fs::write(operations_path(&shard_path), b"{not-json}\n").unwrap();

        let error = TantivyEngine::default()
            .recover_index_from_manifest("logs-000001", schema, &shard_path)
            .unwrap_err();

        assert_eq!(error.status_code(), 500);
        assert!(error
            .opensearch_reason()
            .contains("failed to parse operation log"));

        let _ = std::fs::remove_dir_all(shard_path);
    }

    #[test]
    fn engine_rejects_recovery_with_corrupt_manifest_checksum() {
        let engine = TantivyEngine::default();
        let create = CreateIndexRequest {
            index: "logs-000001".to_string(),
            settings: serde_json::json!({}),
            mappings: serde_json::json!({
                "properties": {
                    "message": { "type": "text" }
                }
            }),
        };
        let schema = map_opensearch_index_to_tantivy_schema(&create).unwrap();
        engine.create_index(create).unwrap();
        let shard_path = unique_temp_path("os-tantivy-corrupt-manifest");
        engine
            .persist_shard_state("logs-000001", &shard_path)
            .unwrap();
        let manifest_path = ShardManifest::manifest_path(&shard_path);
        let tampered = std::fs::read_to_string(&manifest_path)
            .unwrap()
            .replace("\"primary_term\": 1", "\"primary_term\": 2");
        std::fs::write(&manifest_path, tampered).unwrap();

        let error = TantivyEngine::default()
            .recover_index_from_manifest("logs-000001", schema, &shard_path)
            .unwrap_err();

        assert_eq!(error.status_code(), 500);
        assert!(error.opensearch_reason().contains("checksum mismatch"));

        let _ = std::fs::remove_dir_all(shard_path);
    }

    #[test]
    fn engine_rejects_recovery_when_operation_log_is_missing() {
        let engine = TantivyEngine::default();
        let create = CreateIndexRequest {
            index: "logs-000001".to_string(),
            settings: serde_json::json!({}),
            mappings: serde_json::json!({
                "properties": {
                    "message": { "type": "text" }
                }
            }),
        };
        let schema = map_opensearch_index_to_tantivy_schema(&create).unwrap();
        engine.create_index(create).unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({ "message": "hello" }),
            })
            .unwrap();
        let shard_path = unique_temp_path("os-tantivy-missing-operation-log");
        engine
            .persist_shard_state("logs-000001", &shard_path)
            .unwrap();
        std::fs::remove_file(operations_path(&shard_path)).unwrap();

        let error = TantivyEngine::default()
            .recover_index_from_manifest("logs-000001", schema, &shard_path)
            .unwrap_err();

        assert_eq!(error.status_code(), 500);
        assert!(error.opensearch_reason().contains("missing operation log"));

        let _ = std::fs::remove_dir_all(shard_path);
    }

    #[test]
    fn engine_rejects_recovery_with_truncated_vector_metadata() {
        let (engine, schema) = persisted_vectors_fixture();
        let shard_path = unique_temp_path("os-tantivy-truncated-vector-metadata");
        engine.persist_shard_state("vectors", &shard_path).unwrap();
        let operation_path = operations_path(&shard_path);
        let first_line = std::fs::read_to_string(&operation_path)
            .unwrap()
            .lines()
            .next()
            .unwrap()
            .to_string();
        let mut operation = serde_json::from_str::<serde_json::Value>(&first_line).unwrap();
        operation["vector_fields"]["embedding"]["values"] = serde_json::json!([1.0, 0.0]);
        std::fs::write(
            &operation_path,
            format!("{}\n", serde_json::to_string(&operation).unwrap()),
        )
        .unwrap();

        let error = TantivyEngine::default()
            .recover_index_from_manifest("vectors", schema, &shard_path)
            .unwrap_err();

        assert_eq!(error.status_code(), 400);
        assert!(error
            .opensearch_reason()
            .contains("query vector for field [embedding] has dimension [2]"));

        let _ = std::fs::remove_dir_all(shard_path);
    }

    #[test]
    fn engine_rejects_recovery_with_invalid_hnsw_segment_metadata() {
        let (engine, schema) = persisted_vectors_fixture();
        let shard_path = unique_temp_path("os-tantivy-invalid-hnsw-segment");
        let mut manifest = engine.persist_shard_state("vectors", &shard_path).unwrap();
        manifest.vector_segments[0].ann_graph = Some("corrupt-hnsw".to_string());
        persist_shard_manifest(&shard_path, &manifest).unwrap();

        let error = TantivyEngine::default()
            .recover_index_from_manifest("vectors", schema, &shard_path)
            .unwrap_err();

        assert_eq!(error.status_code(), 500);
        assert!(error
            .opensearch_reason()
            .contains("invalid HNSW graph metadata"));

        let _ = std::fs::remove_dir_all(shard_path);
    }

    #[test]
    fn engine_rejects_recovery_when_operation_log_record_is_corrupt() {
        let (engine, schema) = persisted_logs_fixture();
        let shard_path = unique_temp_path("os-tantivy-corrupt-operation-log");
        engine
            .persist_shard_state("logs-000001", &shard_path)
            .unwrap();
        std::fs::write(operations_path(&shard_path), b"{not valid json}\n").unwrap();

        let error = TantivyEngine::default()
            .recover_index_from_manifest("logs-000001", schema, &shard_path)
            .unwrap_err();

        assert_eq!(error.status_code(), 500);
        assert_eq!(error.opensearch_error_type(), "engine_exception");
        assert!(error
            .opensearch_reason()
            .contains("failed to parse operation log"));

        let _ = std::fs::remove_dir_all(shard_path);
    }

    #[test]
    fn engine_rejects_recovery_when_manifest_checksum_is_corrupt() {
        let (engine, schema) = persisted_logs_fixture();
        let shard_path = unique_temp_path("os-tantivy-corrupt-manifest-checksum");
        engine
            .persist_shard_state("logs-000001", &shard_path)
            .unwrap();
        let manifest_path = ShardManifest::manifest_path(&shard_path);
        let mut envelope: serde_json::Value =
            serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
        envelope["checksum"] = serde_json::json!(0_u64);
        std::fs::write(
            &manifest_path,
            serde_json::to_vec_pretty(&envelope).unwrap(),
        )
        .unwrap();

        let error = TantivyEngine::default()
            .recover_index_from_manifest("logs-000001", schema, &shard_path)
            .unwrap_err();

        assert_eq!(error.status_code(), 500);
        assert_eq!(error.opensearch_error_type(), "engine_exception");
        assert!(error.opensearch_reason().contains("checksum mismatch"));

        let _ = std::fs::remove_dir_all(shard_path);
    }

    #[test]
    fn engine_rejects_recovery_when_persisted_operation_segment_is_missing() {
        let (engine, schema) = persisted_logs_fixture();
        let shard_path = unique_temp_path("os-tantivy-missing-operation-segment");
        engine
            .persist_shard_state("logs-000001", &shard_path)
            .unwrap();
        std::fs::remove_file(operations_path(&shard_path)).unwrap();

        let error = TantivyEngine::default()
            .recover_index_from_manifest("logs-000001", schema, &shard_path)
            .unwrap_err();

        assert_eq!(error.status_code(), 500);
        assert_eq!(error.opensearch_error_type(), "engine_exception");
        assert!(error.opensearch_reason().contains("missing operation log"));

        let _ = std::fs::remove_dir_all(shard_path);
    }

    #[test]
    fn engine_rejects_recovery_when_vector_metadata_is_truncated() {
        let (engine, schema) = vector_engine_with_documents();
        let shard_path = unique_temp_path("os-tantivy-truncated-vector-metadata");
        engine.persist_shard_state("vectors", &shard_path).unwrap();
        std::fs::write(
            ShardManifest::manifest_path(&shard_path),
            br#"{"manifest":{"vector_segments":["#,
        )
        .unwrap();

        let error = TantivyEngine::default()
            .recover_index_from_manifest("vectors", schema, &shard_path)
            .unwrap_err();

        assert_eq!(error.status_code(), 500);
        assert_eq!(error.opensearch_error_type(), "engine_exception");
        assert!(error
            .opensearch_reason()
            .contains("failed to parse shard manifest"));

        let _ = std::fs::remove_dir_all(shard_path);
    }

    #[test]
    fn engine_rejects_recovery_when_hnsw_snapshot_metadata_is_invalid() {
        let (engine, schema) = vector_engine_with_documents();
        let shard_path = unique_temp_path("os-tantivy-invalid-hnsw-metadata");
        let mut manifest = engine.persist_shard_state("vectors", &shard_path).unwrap();
        manifest.vector_segments[0].ann_graph = Some("corrupt-hnsw".to_string());
        let envelope = serde_json::json!({
            "manifest": manifest,
            "checksum": shard_manifest_checksum(&manifest).unwrap()
        });
        std::fs::write(
            ShardManifest::manifest_path(&shard_path),
            serde_json::to_vec_pretty(&envelope).unwrap(),
        )
        .unwrap();

        let error = TantivyEngine::default()
            .recover_index_from_manifest("vectors", schema, &shard_path)
            .unwrap_err();

        assert_eq!(error.status_code(), 500);
        assert_eq!(error.opensearch_error_type(), "engine_exception");
        assert!(error
            .opensearch_reason()
            .contains("invalid HNSW graph metadata"));

        let _ = std::fs::remove_dir_all(shard_path);
    }

    #[test]
    fn engine_bounds_and_invalidates_knn_runtime_cache_entries() {
        let (engine, _) = vector_engine_with_documents();
        engine
            .refresh(RefreshRequest {
                indices: vec!["vectors".to_string()],
            })
            .unwrap();

        for query_index in 0..(MAX_KNN_CACHE_ENTRIES_PER_FIELD + 4) {
            engine
                .search(SearchRequest {
                    indices: vec!["vectors".to_string()],
                    query: serde_json::json!({
                        "knn": {
                            "embedding": {
                                "vector": [query_index as f32, 1.0, 0.0],
                                "k": 1
                            }
                        }
                    }),
                    aggregations: serde_json::json!({}),
                    sort: Vec::new(),
                    from: 0,
                    size: 1,
                })
                .unwrap();
        }

        {
            let store = engine
                .store
                .lock()
                .expect("tantivy engine store mutex poisoned");
            let index = store.indices.get("vectors").unwrap();
            let field_cache = index.runtime_cache.knn_search_by_field.get("embedding").unwrap();
            assert!(field_cache.entries.len() <= MAX_KNN_CACHE_ENTRIES_PER_FIELD);
            assert!(field_cache.resident_bytes <= MAX_KNN_CACHE_BYTES_PER_FIELD);
            assert!(!field_cache.entries.is_empty());
        }

        engine
            .refresh(RefreshRequest {
                indices: vec!["vectors".to_string()],
            })
            .unwrap();

        let telemetry = engine.search_cache_telemetry_snapshot().unwrap();
        assert_eq!(telemetry.request_result_cache_entries, 0);
        assert_eq!(telemetry.request_result_cache_resets, 1);
        assert!(telemetry.request_result_cache_invalidated_entries > 0);
        assert!(telemetry.request_result_cache_capacity_evictions > 0);
        assert!(telemetry.request_result_cache_refresh_invalidations > 0);
        assert_eq!(telemetry.request_result_cache_stale_invalidations, 0);
        assert_eq!(telemetry.vector_graph_cache_entries, 0);
        assert_eq!(telemetry.vector_graph_cache_resets, 1);
        assert!(telemetry.vector_graph_cache_invalidated_entries > 0);
        assert_eq!(
            telemetry.vector_graph_cache_refresh_invalidations,
            telemetry.vector_graph_cache_invalidated_entries
        );
        assert_eq!(telemetry.vector_graph_cache_stale_invalidations, 0);
        assert_eq!(telemetry.fast_field_cache_entries, 0);
        assert_eq!(telemetry.fast_field_cache_resets, 1);
        assert_eq!(telemetry.fast_field_cache_invalidated_entries, 0);
        assert_eq!(telemetry.fast_field_cache_refresh_invalidations, 0);
        assert_eq!(telemetry.fast_field_cache_stale_invalidations, 0);

        let store = engine
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let index = store.indices.get("vectors").unwrap();
        let field_cache = index.runtime_cache.knn_search_by_field.get("embedding").unwrap();
        assert!(field_cache.entries.is_empty());
        assert!(field_cache.refresh_invalidations > 0);
    }

    #[test]
    fn stale_knn_cache_drops_are_tracked_separately_from_refresh_and_capacity() {
        let (engine, _) = vector_engine_with_documents();
        engine
            .refresh(RefreshRequest {
                indices: vec!["vectors".to_string()],
            })
            .unwrap();
        let request = SearchRequest {
            indices: vec!["vectors".to_string()],
            query: serde_json::json!({
                "knn": {
                    "embedding": {
                        "vector": [1.0, 0.0, 0.0],
                        "k": 1
                    }
                }
            }),
            aggregations: serde_json::json!({}),
            sort: Vec::new(),
            from: 0,
            size: 1,
        };
        engine.search(request.clone()).unwrap();
        {
            let mut store = engine
                .store
                .lock()
                .expect("tantivy engine store mutex poisoned");
            let index = store.indices.get_mut("vectors").unwrap();
            index.refreshed_seq_no = index.refreshed_seq_no.saturating_add(1);
        }
        engine.search(request).unwrap();

        let telemetry = engine.search_cache_telemetry_snapshot().unwrap();
        assert!(telemetry.request_result_cache_stale_invalidations > 0);
        assert_eq!(telemetry.request_result_cache_refresh_invalidations, 0);

        let details = engine.search_cache_telemetry_details().unwrap();
        let embedding = &details.indices["vectors"].request_result_cache_fields["embedding"];
        assert!(embedding.request_result_cache_stale_invalidations > 0);
        assert_eq!(embedding.request_result_cache_refresh_invalidations, 0);
    }

    #[test]
    fn engine_rejects_document_writes_to_missing_indices() {
        let engine = TantivyEngine::default();

        let error = engine
            .index_document(IndexDocumentRequest {
                index: "missing".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({}),
            })
            .unwrap_err();

        assert_eq!(error.status_code(), 404);
        assert_eq!(error.opensearch_error_type(), "index_not_found_exception");
        assert_eq!(error.opensearch_reason(), "no such index [missing]");
    }

    #[test]
    fn engine_refreshes_and_searches_visible_documents() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "message": { "type": "text" }
                    }
                }),
            })
            .unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({ "message": "hello" }),
            })
            .unwrap();

        let before_refresh = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "match_all": {} }),
                aggregations: serde_json::json!({}),
                sort: Vec::new(),
                from: 0,
                size: 10,
            })
            .unwrap();
        engine
            .refresh(RefreshRequest {
                indices: vec!["logs-000001".to_string()],
            })
            .unwrap();
        let after_refresh = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "match_all": {} }),
                aggregations: serde_json::json!({}),
                sort: Vec::new(),
                from: 0,
                size: 10,
            })
            .unwrap();

        assert_eq!(before_refresh.total_hits, 0);
        assert!(before_refresh.hits.is_empty());
        assert_eq!(after_refresh.total_hits, 1);
        assert_eq!(after_refresh.hits[0].metadata.id, "1");
        assert_eq!(after_refresh.hits[0].score, 1.0);
        assert_eq!(after_refresh.hits[0].source["message"], "hello");
        assert_eq!(after_refresh.shards.total, 1);
        assert_eq!(after_refresh.shards.successful, 1);
        assert!(after_refresh.shards.failures.is_empty());
        assert_eq!(
            after_refresh
                .phase_results
                .iter()
                .map(|phase| &phase.phase)
                .collect::<Vec<_>>(),
            vec![
                &SearchPhase::CanMatch,
                &SearchPhase::Query,
                &SearchPhase::Fetch,
                &SearchPhase::Dfs
            ]
        );
        assert_eq!(
            after_refresh
                .fetch_subphases
                .iter()
                .map(|subphase| &subphase.subphase)
                .collect::<Vec<_>>(),
            vec![
                &SearchFetchSubphase::Source,
                &SearchFetchSubphase::Version,
                &SearchFetchSubphase::SeqNoPrimaryTerm,
                &SearchFetchSubphase::StoredFields,
                &SearchFetchSubphase::Highlight,
                &SearchFetchSubphase::Explain
            ]
        );
        assert!(after_refresh.fetch_subphases[0..3]
            .iter()
            .all(|subphase| !subphase.skipped));
        assert!(after_refresh.fetch_subphases[3..]
            .iter()
            .all(|subphase| subphase.skipped));
    }

    #[test]
    fn engine_applies_index_refresh_policy() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "message": { "type": "text" }
                    }
                }),
            })
            .unwrap();

        engine
            .index_document_with_refresh(
                IndexDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: "1".to_string(),
                    source: serde_json::json!({ "message": "none" }),
                },
                RefreshPolicy::None,
            )
            .unwrap();
        let before_immediate = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "match_all": {} }),
                aggregations: serde_json::json!({}),
                sort: Vec::new(),
                from: 0,
                size: 10,
            })
            .unwrap();

        engine
            .index_document_with_refresh(
                IndexDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: "2".to_string(),
                    source: serde_json::json!({ "message": "immediate" }),
                },
                RefreshPolicy::Immediate,
            )
            .unwrap();
        let after_immediate = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "match_all": {} }),
                aggregations: serde_json::json!({}),
                sort: Vec::new(),
                from: 0,
                size: 10,
            })
            .unwrap();
        let visible_ids = after_immediate
            .hits
            .iter()
            .map(|hit| hit.metadata.id.as_str())
            .collect::<Vec<_>>();

        assert_eq!(before_immediate.total_hits, 0);
        assert_eq!(after_immediate.total_hits, 2);
        assert_eq!(visible_ids, vec!["1", "2"]);
    }

    #[test]
    fn engine_applies_wait_for_refresh_policy_to_update_and_delete() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "message": { "type": "text" }
                    }
                }),
            })
            .unwrap();
        engine
            .index_document_with_refresh(
                IndexDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: "1".to_string(),
                    source: serde_json::json!({ "message": "created" }),
                },
                RefreshPolicy::Immediate,
            )
            .unwrap();

        engine
            .update_document_with_refresh(
                UpdateDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: "1".to_string(),
                    doc: serde_json::json!({ "message": "updated" }),
                    doc_as_upsert: false,
                },
                RefreshPolicy::WaitFor,
            )
            .unwrap();
        let after_update = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "match": { "message": "updated" } }),
                aggregations: serde_json::json!({}),
                sort: Vec::new(),
                from: 0,
                size: 10,
            })
            .unwrap();

        engine
            .delete_document_with_refresh(
                DeleteDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: "1".to_string(),
                },
                RefreshPolicy::WaitFor,
            )
            .unwrap();
        let after_delete = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "match_all": {} }),
                aggregations: serde_json::json!({}),
                sort: Vec::new(),
                from: 0,
                size: 10,
            })
            .unwrap();

        assert_eq!(after_update.total_hits, 1);
        assert_eq!(after_update.hits[0].metadata.id, "1");
        assert_eq!(after_update.hits[0].source["message"], "updated");
        assert_eq!(after_delete.total_hits, 0);
        assert!(after_delete.hits.is_empty());
    }

    #[test]
    fn engine_searches_with_normalized_query_plan() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "message": { "type": "text" },
                        "service": { "type": "keyword" },
                        "bytes": { "type": "long" },
                        "level": { "type": "keyword" }
                    }
                }),
            })
            .unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({
                    "message": "request completed",
                    "service": "api",
                    "bytes": 120,
                    "level": "info"
                }),
            })
            .unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "2".to_string(),
                source: serde_json::json!({
                    "message": "debug request",
                    "service": "worker",
                    "bytes": 90,
                    "level": "debug"
                }),
            })
            .unwrap();
        engine
            .refresh(RefreshRequest {
                indices: vec!["logs-000001".to_string()],
            })
            .unwrap();

        let search = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({
                    "bool": {
                        "must": {
                            "match": {
                                "message": "request"
                            }
                        },
                        "filter": [
                            {
                                "term": {
                                    "service": "api"
                                }
                            },
                            {
                                "range": {
                                    "bytes": {
                                        "gte": 100
                                    }
                                }
                            }
                        ],
                        "must_not": {
                            "term": {
                                "level": "debug"
                            }
                        }
                    }
                }),
                aggregations: serde_json::json!({}),
                sort: Vec::new(),
                from: 0,
                size: 10,
            })
            .unwrap();

        assert_eq!(search.total_hits, 1);
        assert_eq!(search.hits[0].metadata.id, "1");
        assert_eq!(search.hits[0].source["service"], "api");
    }

    #[test]
    fn engine_searches_with_source_derived_query_clauses() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "message": { "type": "text" },
                        "service": { "type": "keyword" },
                        "tags": { "type": "keyword" }
                    }
                }),
            })
            .unwrap();

        for (id, source) in [
            (
                "1",
                serde_json::json!({
                    "message": "Error from API",
                    "service": "api",
                    "tags": ["prod", "blue"]
                }),
            ),
            (
                "2",
                serde_json::json!({
                    "message": "worker completed",
                    "service": "worker",
                    "tags": ["batch"]
                }),
            ),
            ("3", serde_json::json!({ "message": "missing service" })),
        ] {
            engine
                .index_document(IndexDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: id.to_string(),
                    source,
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["logs-000001".to_string()],
            })
            .unwrap();

        let ids = |query| {
            engine
                .search(SearchRequest {
                    indices: vec!["logs-000001".to_string()],
                    query,
                    aggregations: serde_json::json!({}),
                    sort: Vec::new(),
                    from: 0,
                    size: 10,
                })
                .unwrap()
                .hits
                .into_iter()
                .map(|hit| hit.metadata.id)
                .collect::<Vec<_>>()
        };

        assert_eq!(
            ids(serde_json::json!({ "match_none": {} })),
            Vec::<String>::new()
        );
        assert_eq!(
            ids(serde_json::json!({ "ids": { "values": ["2"] } })),
            vec!["2"]
        );
        assert_eq!(
            ids(serde_json::json!({ "exists": { "field": "service" } })),
            vec!["1", "2"]
        );
        assert_eq!(
            ids(serde_json::json!({ "terms": { "tags": ["prod", "green"] } })),
            vec!["1"]
        );
        assert_eq!(
            ids(serde_json::json!({ "prefix": { "service": "wo" } })),
            vec!["2"]
        );
        assert_eq!(
            ids(serde_json::json!({
                "wildcard": {
                    "message": {
                        "value": "err*api",
                        "case_insensitive": true
                    }
                }
            })),
            vec!["1"]
        );
    }

    #[test]
    fn engine_sorts_before_paginating_search_hits() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "bytes": { "type": "long" }
                    }
                }),
            })
            .unwrap();

        for (id, bytes) in [("1", 30), ("2", 10), ("3", 20)] {
            engine
                .index_document(IndexDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: id.to_string(),
                    source: serde_json::json!({
                        "bytes": bytes
                    }),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["logs-000001".to_string()],
            })
            .unwrap();

        let search = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "match_all": {} }),
                aggregations: serde_json::json!({}),
                sort: vec![SortSpec {
                    field: "bytes".to_string(),
                    order: SortOrder::Desc,
                }],
                from: 1,
                size: 1,
            })
            .unwrap();

        assert_eq!(search.total_hits, 3);
        assert_eq!(search.hits.len(), 1);
        assert_eq!(search.hits[0].metadata.id, "3");
        assert_eq!(search.hits[0].source["bytes"], 20);
    }

    #[test]
    fn engine_collects_terms_aggregations_from_filtered_hits_before_pagination() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "service": { "type": "keyword" },
                        "level": { "type": "keyword" }
                    }
                }),
            })
            .unwrap();

        for (id, service, level) in [
            ("1", "api", "info"),
            ("2", "api", "info"),
            ("3", "worker", "debug"),
        ] {
            engine
                .index_document(IndexDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: id.to_string(),
                    source: serde_json::json!({
                        "service": service,
                        "level": level
                    }),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["logs-000001".to_string()],
            })
            .unwrap();

        let search = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({
                    "term": {
                        "level": "info"
                    }
                }),
                aggregations: serde_json::json!({
                    "by_service": {
                        "terms": {
                            "field": "service",
                            "size": 10
                        }
                    }
                }),
                sort: Vec::new(),
                from: 0,
                size: 1,
            })
            .unwrap();

        assert_eq!(search.total_hits, 2);
        assert_eq!(search.hits.len(), 1);
        assert_eq!(
            search.aggregations["by_service"]["buckets"],
            serde_json::json!([
                {
                    "key": "api",
                    "doc_count": 2
                }
            ])
        );
    }

    #[test]
    fn terms_aggregation_response_preserves_opensearch_shape() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "service": { "type": "keyword" }
                    }
                }),
            })
            .unwrap();

        for (id, service) in [("1", "api"), ("2", "api"), ("3", "worker")] {
            engine
                .index_document(IndexDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: id.to_string(),
                    source: serde_json::json!({
                        "service": service
                    }),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["logs-000001".to_string()],
            })
            .unwrap();

        let body = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "match_all": {} }),
                aggregations: serde_json::json!({
                    "by_service": {
                        "terms": {
                            "field": "service",
                            "size": 2
                        }
                    }
                }),
                sort: Vec::new(),
                from: 0,
                size: 10,
            })
            .unwrap()
            .to_opensearch_body(0);

        assert_eq!(body["hits"]["total"]["value"], 3);
        assert_eq!(
            body["aggregations"],
            serde_json::json!({
                "by_service": {
                    "buckets": [
                        {
                            "key": "api",
                            "doc_count": 2
                        },
                        {
                            "key": "worker",
                            "doc_count": 1
                        }
                    ]
                }
            })
        );
    }

    #[test]
    fn engine_collects_metric_aggregations_from_filtered_hits() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "bytes": { "type": "long" },
                        "level": { "type": "keyword" }
                    }
                }),
            })
            .unwrap();

        for (id, bytes, level) in [("1", 100, "info"), ("2", 200, "info"), ("3", 500, "debug")] {
            engine
                .index_document(IndexDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: id.to_string(),
                    source: serde_json::json!({
                        "bytes": bytes,
                        "level": level
                    }),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["logs-000001".to_string()],
            })
            .unwrap();

        let body = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "term": { "level": "info" } }),
                aggregations: serde_json::json!({
                    "min_bytes": { "min": { "field": "bytes" } },
                    "max_bytes": { "max": { "field": "bytes" } },
                    "sum_bytes": { "sum": { "field": "bytes" } },
                    "avg_bytes": { "avg": { "field": "bytes" } },
                    "count_bytes": { "value_count": { "field": "bytes" } }
                }),
                sort: Vec::new(),
                from: 0,
                size: 1,
            })
            .unwrap()
            .to_opensearch_body(0);

        assert_eq!(body["hits"]["total"]["value"], 2);
        assert_eq!(body["aggregations"]["min_bytes"]["value"], 100.0);
        assert_eq!(body["aggregations"]["max_bytes"]["value"], 200.0);
        assert_eq!(body["aggregations"]["sum_bytes"]["value"], 300.0);
        assert_eq!(body["aggregations"]["avg_bytes"]["value"], 150.0);
        assert_eq!(body["aggregations"]["count_bytes"]["value"], 2.0);
    }

    #[test]
    fn engine_collects_filter_bucket_aggregations_from_filtered_hits() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "level": { "type": "keyword" },
                        "service": { "type": "keyword" }
                    }
                }),
            })
            .unwrap();

        for (id, level, service) in [
            ("1", "error", "api"),
            ("2", "info", "api"),
            ("3", "error", "worker"),
            ("4", "debug", "worker"),
        ] {
            engine
                .index_document(IndexDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: id.to_string(),
                    source: serde_json::json!({
                        "level": level,
                        "service": service
                    }),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["logs-000001".to_string()],
            })
            .unwrap();

        let body = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "term": { "service": "api" } }),
                aggregations: serde_json::json!({
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
                }),
                sort: Vec::new(),
                from: 0,
                size: 1,
            })
            .unwrap()
            .to_opensearch_body(0);

        assert_eq!(body["hits"]["total"]["value"], 2);
        assert_eq!(body["aggregations"]["only_errors"]["doc_count"], 1);
        assert_eq!(
            body["aggregations"]["by_level"]["buckets"],
            serde_json::json!({
                "errors": {
                    "doc_count": 1
                },
                "infos": {
                    "doc_count": 1
                }
            })
        );
    }

    #[test]
    fn engine_collects_top_hits_aggregation_from_filtered_hits() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "level": { "type": "keyword" },
                        "message": { "type": "text" }
                    }
                }),
            })
            .unwrap();

        for (id, level, message) in [
            ("1", "info", "started"),
            ("2", "info", "ready"),
            ("3", "debug", "ignored"),
        ] {
            engine
                .index_document(IndexDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: id.to_string(),
                    source: serde_json::json!({
                        "level": level,
                        "message": message
                    }),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["logs-000001".to_string()],
            })
            .unwrap();

        let body = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "term": { "level": "info" } }),
                aggregations: serde_json::json!({
                    "sample": {
                        "top_hits": {
                            "from": 1,
                            "size": 1
                        }
                    }
                }),
                sort: Vec::new(),
                from: 0,
                size: 0,
            })
            .unwrap()
            .to_opensearch_body(0);

        assert_eq!(body["hits"]["total"]["value"], 2);
        assert_eq!(body["aggregations"]["sample"]["hits"]["total"]["value"], 2);
        assert_eq!(
            body["aggregations"]["sample"]["hits"]["hits"],
            serde_json::json!([
                {
                    "_index": "logs-000001",
                    "_id": "2",
                    "_score": 1.0,
                    "_source": {
                        "level": "info",
                        "message": "ready"
                    },
                    "_version": 1,
                    "_seq_no": 1,
                    "_primary_term": 1
                }
            ])
        );
    }

    #[test]
    fn engine_collects_composite_terms_aggregation_from_filtered_hits() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "service": { "type": "keyword" },
                        "level": { "type": "keyword" }
                    }
                }),
            })
            .unwrap();

        for (id, service, level) in [
            ("1", "api", "info"),
            ("2", "api", "info"),
            ("3", "api", "error"),
            ("4", "worker", "info"),
        ] {
            engine
                .index_document(IndexDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: id.to_string(),
                    source: serde_json::json!({
                        "service": service,
                        "level": level
                    }),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["logs-000001".to_string()],
            })
            .unwrap();

        let body = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "term": { "service": "api" } }),
                aggregations: serde_json::json!({
                    "by_service_level": {
                        "composite": {
                            "size": 10,
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
                }),
                sort: Vec::new(),
                from: 0,
                size: 0,
            })
            .unwrap()
            .to_opensearch_body(0);

        assert_eq!(body["hits"]["total"]["value"], 3);
        assert_eq!(
            body["aggregations"]["by_service_level"]["buckets"],
            serde_json::json!([
                {
                    "key": {
                        "level": "error",
                        "service": "api"
                    },
                    "doc_count": 1
                },
                {
                    "key": {
                        "level": "info",
                        "service": "api"
                    },
                    "doc_count": 2
                }
            ])
        );
        assert_eq!(
            body["aggregations"]["by_service_level"]["after_key"],
            serde_json::json!({
                "level": "info",
                "service": "api"
            })
        );
    }

    #[test]
    fn engine_collects_significant_terms_aggregation_from_filtered_hits() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "service": { "type": "keyword" },
                        "tag": { "type": "keyword" }
                    }
                }),
            })
            .unwrap();

        for (id, service, tag) in [
            ("1", "api", "auth"),
            ("2", "api", "auth"),
            ("3", "api", "billing"),
            ("4", "worker", "auth"),
        ] {
            engine
                .index_document(IndexDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: id.to_string(),
                    source: serde_json::json!({
                        "service": service,
                        "tag": tag
                    }),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["logs-000001".to_string()],
            })
            .unwrap();

        let body = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "term": { "service": "api" } }),
                aggregations: serde_json::json!({
                    "interesting_tags": {
                        "significant_terms": {
                            "field": "tag",
                            "size": 2
                        }
                    }
                }),
                sort: Vec::new(),
                from: 0,
                size: 0,
            })
            .unwrap()
            .to_opensearch_body(0);

        assert_eq!(body["hits"]["total"]["value"], 3);
        assert_eq!(
            body["aggregations"]["interesting_tags"]["buckets"],
            serde_json::json!([
                {
                    "key": "auth",
                    "doc_count": 2,
                    "bg_count": 3,
                    "score": 2.0
                },
                {
                    "key": "billing",
                    "doc_count": 1,
                    "bg_count": 1,
                    "score": 1.0
                }
            ])
        );
        assert_eq!(
            body["aggregations"]["interesting_tags"]["doc_count"],
            serde_json::json!(3)
        );
        assert_eq!(
            body["aggregations"]["interesting_tags"]["bg_count"],
            serde_json::json!(4)
        );
    }

    #[test]
    fn engine_collects_geo_bounds_aggregation_from_filtered_hits() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "stores".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "region": { "type": "keyword" }
                    }
                }),
            })
            .unwrap();

        for (id, region, lat, lon) in [
            ("1", "west", 37.77, -122.42),
            ("2", "west", 34.05, -118.24),
            ("3", "east", 40.71, -74.00),
        ] {
            engine
                .index_document(IndexDocumentRequest {
                    index: "stores".to_string(),
                    id: id.to_string(),
                    source: serde_json::json!({
                        "region": region,
                        "location": {
                            "lat": lat,
                            "lon": lon
                        }
                    }),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["stores".to_string()],
            })
            .unwrap();

        let body = engine
            .search(SearchRequest {
                indices: vec!["stores".to_string()],
                query: serde_json::json!({ "term": { "region": "west" } }),
                aggregations: serde_json::json!({
                    "viewport": {
                        "geo_bounds": {
                            "field": "location"
                        }
                    }
                }),
                sort: Vec::new(),
                from: 0,
                size: 0,
            })
            .unwrap()
            .to_opensearch_body(0);

        assert_eq!(body["hits"]["total"]["value"], 2);
        assert_eq!(
            body["aggregations"]["viewport"],
            serde_json::json!({
                "bounds": {
                    "top_left": {
                        "lat": 37.77,
                        "lon": -122.42
                    },
                    "bottom_right": {
                        "lat": 34.05,
                        "lon": -118.24
                    }
                }
            })
        );
    }

    #[test]
    fn engine_collects_sum_bucket_pipeline_aggregation() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "service": { "type": "keyword" },
                        "level": { "type": "keyword" }
                    }
                }),
            })
            .unwrap();

        for (id, service, level) in [
            ("1", "api", "info"),
            ("2", "api", "info"),
            ("3", "worker", "info"),
            ("4", "worker", "debug"),
        ] {
            engine
                .index_document(IndexDocumentRequest {
                    index: "logs-000001".to_string(),
                    id: id.to_string(),
                    source: serde_json::json!({
                        "service": service,
                        "level": level
                    }),
                })
                .unwrap();
        }
        engine
            .refresh(RefreshRequest {
                indices: vec!["logs-000001".to_string()],
            })
            .unwrap();

        let body = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "term": { "level": "info" } }),
                aggregations: serde_json::json!({
                    "by_service": {
                        "terms": {
                            "field": "service",
                            "size": 10
                        }
                    },
                    "service_doc_total": {
                        "sum_bucket": {
                            "buckets_path": "by_service>_count"
                        }
                    }
                }),
                sort: Vec::new(),
                from: 0,
                size: 0,
            })
            .unwrap()
            .to_opensearch_body(0);

        assert_eq!(body["hits"]["total"]["value"], 3);
        assert_eq!(body["aggregations"]["service_doc_total"]["value"], 3.0);
    }

    #[test]
    fn engine_collects_scripted_metric_placeholder_aggregation() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "service": { "type": "keyword" }
                    }
                }),
            })
            .unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({
                    "service": "api"
                }),
            })
            .unwrap();
        engine
            .refresh(RefreshRequest {
                indices: vec!["logs-000001".to_string()],
            })
            .unwrap();

        let body = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "match_all": {} }),
                aggregations: serde_json::json!({
                    "custom_metric": {
                        "scripted_metric": {
                            "map_script": "return params.value",
                            "params": {
                                "value": {
                                    "count": 7
                                }
                            }
                        }
                    }
                }),
                sort: Vec::new(),
                from: 0,
                size: 0,
            })
            .unwrap()
            .to_opensearch_body(0);

        assert_eq!(
            body["aggregations"]["custom_metric"]["value"],
            serde_json::json!({
                "count": 7
            })
        );
    }

    #[test]
    fn engine_collects_plugin_placeholder_aggregation() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "logs-000001".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "service": { "type": "keyword" }
                    }
                }),
            })
            .unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({
                    "service": "api"
                }),
            })
            .unwrap();
        engine
            .refresh(RefreshRequest {
                indices: vec!["logs-000001".to_string()],
            })
            .unwrap();

        let body = engine
            .search(SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: serde_json::json!({ "match_all": {} }),
                aggregations: serde_json::json!({
                    "custom": {
                        "plugin": {
                            "name": "example-plugin",
                            "kind": "example_metric",
                            "params": {
                                "field": "service"
                            }
                        }
                    }
                }),
                sort: Vec::new(),
                from: 0,
                size: 0,
            })
            .unwrap()
            .to_opensearch_body(0);

        assert_eq!(
            body["aggregations"]["custom"],
            serde_json::json!({
                "value": null,
                "_plugin": "example-plugin",
                "_type": "example_metric",
                "params": {
                    "field": "service"
                }
            })
        );
    }

    #[test]
    fn engine_rejects_malformed_search_queries() {
        let engine = TantivyEngine::default();
        let error = engine
            .search(SearchRequest {
                indices: Vec::new(),
                query: serde_json::json!({ "term": { "service": { "boost": 2.0 } } }),
                aggregations: serde_json::json!({}),
                sort: Vec::new(),
                from: 0,
                size: 10,
            })
            .unwrap_err();

        assert_eq!(error.status_code(), 400);
        assert_eq!(error.opensearch_error_type(), "illegal_argument_exception");
    }

    #[test]
    fn knn_result_cache_is_bounded_and_cleared_on_refresh() {
        let (engine, _) = vector_engine_with_documents();
        engine
            .refresh(RefreshRequest {
                indices: vec!["vectors".to_string()],
            })
            .unwrap();

        for offset in 0..(MAX_KNN_CACHE_ENTRIES_PER_FIELD + 4) {
            let vector = vec![1.0 + offset as f32, offset as f32, 0.0];
            engine
                .search(SearchRequest {
                    indices: vec!["vectors".to_string()],
                    query: serde_json::json!({
                        "knn": {
                            "embedding": {
                                "vector": vector,
                                "k": 5
                            }
                        }
                    }),
                    aggregations: serde_json::json!({}),
                    sort: Vec::new(),
                    from: 0,
                    size: 10,
                })
                .unwrap();
        }

        {
            let store = engine
                .store
                .lock()
                .expect("tantivy engine store mutex poisoned");
            let index = store.indices.get("vectors").expect("vectors index present");
            let field_cache = index
                .runtime_cache
                .knn_search_by_field
                .get("embedding")
                .expect("embedding cache present");
            assert!(field_cache.entries.len() <= MAX_KNN_CACHE_ENTRIES_PER_FIELD);
            assert!(field_cache.resident_bytes <= MAX_KNN_CACHE_BYTES_PER_FIELD);
            assert!(!field_cache.entries.is_empty());
        }

        engine
            .refresh(RefreshRequest {
                indices: vec!["vectors".to_string()],
            })
            .unwrap();

        let store = engine
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let index = store.indices.get("vectors").expect("vectors index present");
        let field_cache = index
            .runtime_cache
            .knn_search_by_field
            .get("embedding")
            .expect("embedding cache telemetry retained");
        assert!(field_cache.entries.is_empty());
        assert_eq!(field_cache.resident_bytes, 0);
        drop(store);

        let details = engine.search_cache_telemetry_details().unwrap();
        let vectors = details.indices.get("vectors").expect("vectors cache detail");
        assert!(
            vectors
                .request_result_cache_fields
                .get("embedding")
                .expect("embedding request-result detail")
                .request_result_cache_resets
                > 0
        );
        assert!(
            vectors
                .vector_graph_cache_fields
                .get("embedding")
                .expect("embedding vector-graph detail")
                .vector_graph_cache_resets
                > 0
        );
        assert!(vectors.fast_field_cache_fields.is_empty());
    }

    #[test]
    fn search_populates_distinct_runtime_cache_surfaces() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "vectors".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "service": { "type": "keyword" },
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 3,
                            "space_type": "l2"
                        }
                    }
                }),
            })
            .unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "vectors".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({
                    "service": "api",
                    "embedding": [1.0, 0.0, 0.0]
                }),
            })
            .unwrap();
        engine
            .refresh(RefreshRequest {
                indices: vec!["vectors".to_string()],
            })
            .unwrap();

        engine
            .search(SearchRequest {
                indices: vec!["vectors".to_string()],
                query: serde_json::json!({
                    "knn": {
                        "embedding": {
                            "vector": [1.0, 0.0, 0.0],
                            "k": 5
                        }
                    }
                }),
                aggregations: serde_json::json!({
                    "services": { "terms": { "field": "service" } }
                }),
                sort: vec![SortSpec {
                    field: "service".to_string(),
                    order: SortOrder::Asc,
                }],
                from: 0,
                size: 10,
            })
            .unwrap();

        let store = engine
            .store
            .lock()
            .expect("tantivy engine store mutex poisoned");
        let index = store.indices.get("vectors").expect("vectors index present");
        assert!(index.runtime_cache.knn_search_by_field.contains_key("embedding"));
        assert!(
            index
                .runtime_cache
                .vector_graph_by_field
                .entries
                .contains_key("embedding")
        );
        assert!(
            index
                .runtime_cache
                .fast_fields_by_name
                .entries
                .contains_key("service")
        );
    }

    #[test]
    fn search_cache_telemetry_tracks_hits_misses_and_evictions_per_surface() {
        let engine = TantivyEngine::default();
        engine
            .create_index(CreateIndexRequest {
                index: "vectors".to_string(),
                settings: serde_json::json!({}),
                mappings: serde_json::json!({
                    "properties": {
                        "service": { "type": "keyword" },
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 3,
                            "space_type": "l2"
                        }
                    }
                }),
            })
            .unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "vectors".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({
                    "service": "api",
                    "embedding": [1.0, 0.0, 0.0]
                }),
            })
            .unwrap();
        engine
            .refresh(RefreshRequest {
                indices: vec!["vectors".to_string()],
            })
            .unwrap();

        let base_search = || SearchRequest {
            indices: vec!["vectors".to_string()],
            query: serde_json::json!({
                "knn": {
                    "embedding": {
                        "vector": [1.0, 0.0, 0.0],
                        "k": 5
                    }
                }
            }),
            aggregations: serde_json::json!({
                "services": { "terms": { "field": "service" } }
            }),
            sort: vec![SortSpec {
                field: "service".to_string(),
                order: SortOrder::Asc,
            }],
            from: 0,
            size: 10,
        };

        engine.search(base_search()).unwrap();
        engine.search(base_search()).unwrap();

        for offset in 0..(MAX_KNN_CACHE_ENTRIES_PER_FIELD + 4) {
            engine
                .search(SearchRequest {
                    indices: vec!["vectors".to_string()],
                    query: serde_json::json!({
                        "knn": {
                            "embedding": {
                                "vector": [1.0 + offset as f32, offset as f32, 0.0],
                                "k": 5
                            }
                        }
                    }),
                    aggregations: serde_json::json!({
                        "services": { "terms": { "field": "service" } }
                    }),
                    sort: vec![SortSpec {
                        field: "service".to_string(),
                        order: SortOrder::Asc,
                    }],
                    from: 0,
                    size: 10,
                })
                .unwrap();
        }

        let telemetry = engine.search_cache_telemetry_snapshot().unwrap();
        let details = engine.search_cache_telemetry_details().unwrap();
        let vectors = details.indices.get("vectors").expect("vectors cache detail");
        let request_result_field = vectors
            .request_result_cache_fields
            .get("embedding")
            .expect("embedding request-result detail");
        let vector_graph_field = vectors
            .vector_graph_cache_fields
            .get("embedding")
            .expect("embedding vector-graph detail");
        let fast_field = vectors
            .fast_field_cache_fields
            .get("service")
            .expect("service fast-field detail");
        assert!(telemetry.request_result_cache_entries <= MAX_KNN_CACHE_ENTRIES_PER_FIELD);
        assert!(telemetry.request_result_cache_hits > 0);
        assert!(telemetry.request_result_cache_misses > 0);
        assert!(telemetry.request_result_cache_evictions > 0);
        assert!(telemetry.request_result_cache_capacity_evictions > 0);
        assert!(vectors.request_result_cache_oldest_entry_age_ticks >= vectors.request_result_cache_newest_entry_age_ticks);
        assert!(request_result_field.request_result_cache_oldest_entry_age_ticks >= request_result_field.request_result_cache_newest_entry_age_ticks);
        assert!(request_result_field.request_result_cache_hits > 0);
        assert!(request_result_field.request_result_cache_misses > 0);
        assert!(request_result_field.request_result_cache_evictions > 0);
        assert!(request_result_field.request_result_cache_capacity_evictions > 0);
        assert_eq!(request_result_field.request_result_cache_refresh_invalidations, 0);
        assert_eq!(request_result_field.request_result_cache_stale_invalidations, 0);
        assert_eq!(telemetry.vector_graph_cache_entries, 1);
        assert!(telemetry.vector_graph_cache_hits > 0);
        assert!(telemetry.vector_graph_cache_misses > 0);
        assert_eq!(telemetry.vector_graph_cache_evictions, 0);
        assert!(vectors.vector_graph_cache_oldest_entry_age_ticks >= vectors.vector_graph_cache_newest_entry_age_ticks);
        assert!(vector_graph_field.vector_graph_cache_hits > 0);
        assert!(vector_graph_field.vector_graph_cache_misses > 0);
        assert_eq!(vector_graph_field.vector_graph_cache_capacity_evictions, 0);
        assert_eq!(vector_graph_field.vector_graph_cache_refresh_invalidations, 0);
        assert_eq!(vector_graph_field.vector_graph_cache_stale_invalidations, 0);
        assert_eq!(telemetry.fast_field_cache_entries, 1);
        assert!(telemetry.fast_field_cache_hits > 0);
        assert!(telemetry.fast_field_cache_misses > 0);
        assert_eq!(telemetry.fast_field_cache_evictions, 0);
        assert!(vectors.fast_field_cache_oldest_entry_age_ticks >= vectors.fast_field_cache_newest_entry_age_ticks);
        assert!(fast_field.fast_field_cache_hits > 0);
        assert!(fast_field.fast_field_cache_misses > 0);
        assert_eq!(fast_field.fast_field_cache_capacity_evictions, 0);
        assert_eq!(fast_field.fast_field_cache_refresh_invalidations, 0);
        assert_eq!(fast_field.fast_field_cache_stale_invalidations, 0);
    }

    fn field<'a>(schema: &'a TantivyIndexSchema, name: &str) -> &'a TantivyFieldMapping {
        schema
            .fields
            .iter()
            .find(|field| field.name == name)
            .unwrap()
    }

    fn hit_ids(hits: &[VectorSearchHit]) -> Vec<&str> {
        hits.iter().map(|hit| hit.id.as_str()).collect()
    }

    fn search_hit_ids(hits: &[SearchHit]) -> Vec<&str> {
        hits.iter().map(|hit| hit.metadata.id.as_str()).collect()
    }

    fn persisted_logs_fixture() -> (TantivyEngine, TantivyIndexSchema) {
        let engine = TantivyEngine::default();
        let create = CreateIndexRequest {
            index: "logs-000001".to_string(),
            settings: serde_json::json!({}),
            mappings: serde_json::json!({
                "properties": {
                    "message": { "type": "text" }
                }
            }),
        };
        let schema = map_opensearch_index_to_tantivy_schema(&create).unwrap();
        engine.create_index(create).unwrap();
        engine
            .index_document(IndexDocumentRequest {
                index: "logs-000001".to_string(),
                id: "1".to_string(),
                source: serde_json::json!({ "message": "hello" }),
            })
            .unwrap();
        (engine, schema)
    }

    fn vector_engine_with_documents() -> (TantivyEngine, TantivyIndexSchema) {
        let engine = TantivyEngine::default();
        let create = CreateIndexRequest {
            index: "vectors".to_string(),
            settings: serde_json::json!({}),
            mappings: serde_json::json!({
                "properties": {
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 3,
                        "space_type": "l2"
                    }
                }
            }),
        };
        let schema = map_opensearch_index_to_tantivy_schema(&create).unwrap();
        engine.create_index(create).unwrap();
        for (id, embedding) in [
            ("a", serde_json::json!([1.0, 0.0, 0.0])),
            ("b", serde_json::json!([0.0, 1.0, 0.0])),
        ] {
            engine
                .index_document(IndexDocumentRequest {
                    index: "vectors".to_string(),
                    id: id.to_string(),
                    source: serde_json::json!({
                        "embedding": embedding,
                        "name": id
                    }),
                })
                .unwrap();
        }
        (engine, schema)
    }

    fn persisted_vectors_fixture() -> (TantivyEngine, TantivyIndexSchema) {
        vector_engine_with_documents()
    }

    fn unique_temp_path(name: &str) -> std::path::PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock should be after unix epoch")
            .as_nanos();
        std::env::temp_dir().join(format!("{name}-{}-{nanos}", std::process::id()))
    }
}
