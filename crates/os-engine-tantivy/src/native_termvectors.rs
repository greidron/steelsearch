use super::*;
use tantivy::collector::DocSetCollector;
use tantivy::{DocSet, Postings, SearcherGeneration};

#[derive(Clone, Debug)]
pub struct NativeTermVectorOptions {
    pub fields: Option<BTreeSet<String>>,
    pub per_field_analyzer: BTreeMap<String, String>,
    pub positions: bool,
    pub offsets: bool,
    pub field_statistics: bool,
    pub term_statistics: bool,
}

impl Default for NativeTermVectorOptions {
    fn default() -> Self {
        Self {
            fields: None,
            per_field_analyzer: BTreeMap::new(),
            positions: true,
            offsets: true,
            field_statistics: true,
            term_statistics: false,
        }
    }
}

#[derive(Clone, Debug)]
pub struct NativeTermVectorResponse {
    pub document: GetDocumentResponse,
    pub fields: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Default)]
pub(super) struct InternalReaderCache(Arc<Mutex<Option<InternalReader>>>);

#[derive(Debug)]
struct InternalReader {
    schema_hash: u64,
    generation: (i64, u64, u64),
    state: TantivySearchState,
    documents: BTreeMap<String, Arc<StoredDocument>>,
}

impl InternalReader {
    fn apply_documents(
        &mut self,
        documents: &BTreeMap<String, Arc<StoredDocument>>,
    ) -> EngineResult<()> {
        let removed = self
            .documents
            .iter()
            .filter(|(id, previous)| {
                documents
                    .get(*id)
                    .map_or(true, |current| !Arc::ptr_eq(previous, current))
            })
            .map(|(id, _)| id)
            .collect::<Vec<_>>();
        let prepared = documents
            .iter()
            .filter(|(id, current)| {
                self.documents
                    .get(*id)
                    .map_or(true, |previous| !Arc::ptr_eq(previous, current))
            })
            .map(|(_, document)| {
                build_tantivy_document(&self.state.index, &self.state.fields, document)
            })
            .collect::<EngineResult<Vec<_>>>()?;
        if !removed.is_empty() || !prepared.is_empty() {
            let mut writer = self
                .state
                .writer
                .lock()
                .expect("internal native writer mutex poisoned");
            let id_field = self.state.fields["_id"].field;
            for id in removed {
                writer.delete_term(Term::from_field_text(id_field, id));
            }
            for document in prepared {
                writer.add_document(document).map_err(tantivy_error)?;
            }
            writer.commit().map_err(tantivy_error)?;
            drop(writer);
            self.state.reader.reload().map_err(tantivy_error)?;
            self.state.searcher = self.state.reader.searcher();
        }
        self.documents = documents.clone();
        Ok(())
    }
}

#[derive(Clone, Debug, Default)]
pub(super) struct FieldStatisticsCache(Arc<Mutex<Option<CachedStatistics>>>);

#[derive(Clone, Debug)]
struct CachedStatistics {
    generation: SearcherGeneration,
    fields: BTreeMap<Field, Value>,
}

impl FieldStatisticsCache {
    fn read(&self, state: &TantivySearchState, field: Field) -> EngineResult<Value> {
        let mut cache = self.0.lock().expect("termvector statistics cache poisoned");
        let generation = state.searcher.generation();
        if cache
            .as_ref()
            .map_or(true, |cache| &cache.generation != generation)
        {
            *cache = Some(CachedStatistics {
                generation: generation.clone(),
                fields: BTreeMap::new(),
            });
        }
        let cache = cache.as_mut().expect("cache initialized");
        if let Some(statistics) = cache.fields.get(&field) {
            return Ok(statistics.clone());
        }
        let mut doc_count = 0u64;
        let mut sum_doc_freq = 0u64;
        let mut sum_ttf = 0u64;
        // Native field totals are computed once per reader generation, never from source scans.
        // Like Lucene field statistics, these include unmerged deleted postings.
        for segment in state.searcher.segment_readers() {
            let inverted = segment.inverted_index(field).map_err(tantivy_error)?;
            let mut documents = BTreeSet::new();
            let mut terms = inverted.terms().stream().map_err(tantivy_error)?;
            while terms.advance() {
                sum_doc_freq += u64::from(terms.value().doc_freq);
                let mut postings = inverted
                    .read_postings_from_terminfo(terms.value(), IndexRecordOption::WithFreqs)
                    .map_err(tantivy_error)?;
                while postings.doc() != tantivy::TERMINATED {
                    documents.insert(postings.doc());
                    sum_ttf += u64::from(postings.term_freq());
                    postings.advance();
                }
            }
            doc_count += documents.len() as u64;
        }
        let statistics = serde_json::json!({"doc_count": doc_count,
            "sum_doc_freq": sum_doc_freq, "sum_ttf": sum_ttf});
        cache.fields.insert(field, statistics.clone());
        Ok(statistics)
    }
}

impl TantivyEngine {
    pub fn get_native_termvectors(
        &self,
        request: GetDocumentRequest,
        routing: Option<&str>,
        options: &NativeTermVectorOptions,
        realtime: bool,
    ) -> EngineResult<Option<NativeTermVectorResponse>> {
        if !realtime {
            return self.get_native_refreshed_termvectors(request, routing, options);
        }
        let refresh_lock = {
            let store = self
                .store
                .read()
                .expect("tantivy engine store rwlock poisoned");
            Arc::clone(
                &store
                    .indices
                    .get(&request.index)
                    .ok_or_else(|| EngineError::IndexNotFound {
                        index: request.index.clone(),
                    })?
                    .refresh_lock,
            )
        };
        let _refresh_guard = refresh_lock.lock().expect("index refresh lock poisoned");
        let store = self
            .store
            .read()
            .expect("tantivy engine store rwlock poisoned");
        let index = store
            .indices
            .get(&request.index)
            .filter(|index| Arc::ptr_eq(&index.refresh_lock, &refresh_lock))
            .ok_or_else(|| EngineError::IndexNotFound {
                index: request.index.clone(),
            })?;
        let shard_id = index.documents.shard_id_for_write(&request.id, routing);
        let Some(shard) = index.documents.shards.get(&shard_id) else {
            return Ok(None);
        };
        let Some(document) = shard.get(&request.id) else {
            return Ok(None);
        };
        let generation = (
            index.next_seq_no,
            shard.non_append_generation,
            shard.persistence_rewrite_generation,
        );
        let mut cache = shard
            .internal_termvector_reader
            .0
            .lock()
            .expect("internal termvector reader cache poisoned");
        if cache.as_ref().map_or(true, |cached| {
            cached.generation != generation || cached.schema_hash != index.schema_hash
        }) {
            let mut internal = if let Some(previous) = cache
                .take()
                .filter(|cached| cached.schema_hash == index.schema_hash)
            {
                previous
            } else {
                let (native_schema, _) = build_tantivy_schema(&index.schema);
                let (state, documents) = if let Some(published) = shard
                    .search_state
                    .as_ref()
                    .filter(|state| state.index.schema() == native_schema)
                {
                    // Fork native segment bytes; ordinary refresh retains its own writer and visibility.
                    let directory = published
                        .directory
                        .fork_committed()
                        .map_err(tantivy_error)?;
                    let mut native_index =
                        TantivyIndexHandle::open(directory.clone()).map_err(tantivy_error)?;
                    native_index.set_tokenizers(published.index.tokenizers().clone());
                    let writer = native_index
                        .writer(TANTIVY_WRITER_HEAP_BYTES)
                        .map_err(tantivy_error)?;
                    let mut merge_policy = tantivy::merge_policy::LogMergePolicy::default();
                    merge_policy.set_min_layer_size(TANTIVY_MERGE_MIN_LAYER_DOCS);
                    writer.set_merge_policy(Box::new(merge_policy));
                    (
                        TantivySearchState::from_committed_index(
                            native_index,
                            directory,
                            writer,
                            published.fields.clone(),
                            published.native_text_compatibility.clone(),
                            published.indexed_schema.clone(),
                        )?,
                        shard.refreshed_documents_by_id.as_ref().clone(),
                    )
                } else {
                    // No compatible native schema exists yet; use the normal native indexing path.
                    (
                        TantivySearchState::build_from_documents(
                            &index.schema,
                            shard.values(),
                            i64::MAX,
                        )?,
                        shard.documents.clone(),
                    )
                };
                InternalReader {
                    schema_hash: index.schema_hash,
                    generation,
                    state,
                    documents,
                }
            };
            internal.apply_documents(&shard.documents)?;
            internal.generation = generation;
            *cache = Some(internal);
        }
        let state = &cache.as_ref().expect("internal reader initialized").state;
        render_native_termvectors(request, &index.schema, document, state, options).map(Some)
    }

    pub fn get_native_refreshed_termvectors(
        &self,
        request: GetDocumentRequest,
        routing: Option<&str>,
        options: &NativeTermVectorOptions,
    ) -> EngineResult<Option<NativeTermVectorResponse>> {
        let store = self
            .store
            .read()
            .expect("tantivy engine store rwlock poisoned");
        let index =
            store
                .indices
                .get(&request.index)
                .ok_or_else(|| EngineError::IndexNotFound {
                    index: request.index.clone(),
                })?;
        let shard_id = index.documents.shard_id_for_write(&request.id, routing);
        let Some(shard) = index.documents.shards.get(&shard_id) else {
            return Ok(None);
        };
        let Some(document) = shard.refreshed_document_by_id(&request.id) else {
            return Ok(None);
        };
        let state = shard
            .search_state
            .as_ref()
            .ok_or_else(|| invalid_request("published document has no native reader"))?;
        render_native_termvectors(request, &index.schema, document, state, options).map(Some)
    }
}

fn render_native_termvectors(
    request: GetDocumentRequest,
    schema: &TantivyIndexSchema,
    document: &StoredDocument,
    state: &TantivySearchState,
    options: &NativeTermVectorOptions,
) -> EngineResult<NativeTermVectorResponse> {
    let id_field = state
        .fields
        .get("_id")
        .ok_or_else(|| invalid_request("native id field missing"))?;
    let query = TermQuery::new(
        Term::from_field_text(id_field.field, &request.id),
        IndexRecordOption::Basic,
    );
    let addresses = state
        .searcher
        .search(&query, &DocSetCollector)
        .map_err(tantivy_error)?;
    if addresses.len() != 1 {
        return Err(invalid_request("published document/native reader mismatch"));
    }
    let address = *addresses.iter().next().expect("one address");
    // OpenSearch field selection treats only '*' as a wildcard, not '?'.
    let selected_patterns = options
        .fields
        .as_ref()
        .map(|selected| {
            regex::RegexSetBuilder::new(selected.iter().map(|pattern| {
                format!(
                    "\\A{}\\z",
                    pattern
                        .split('*')
                        .map(regex::escape)
                        .collect::<Vec<_>>()
                        .join(".*")
                )
            }))
            .dot_matches_new_line(true)
            .build()
            .map_err(tantivy_error)
        })
        .transpose()?;
    let mut fields = BTreeMap::new();
    for mapping in &schema.fields {
        if !matches!(
            mapping.field_type,
            TantivyFieldType::Text | TantivyFieldType::Keyword
        ) || !mapping.indexed
        {
            continue;
        }
        let capability = mapping
            .text_options
            .as_ref()
            .and_then(|options| options.term_vector.as_ref())
            .and_then(Value::as_str)
            .unwrap_or("no");
        if let Some(selected) = &selected_patterns {
            if !selected.is_match(&mapping.name) {
                continue;
            }
        } else if capability == "no" {
            continue;
        }
        // An override is generated from the stored source even if native postings have vectors.
        let analyzer_override = options
            .per_field_analyzer
            .get(&mapping.name)
            .map(String::as_str);
        let generated = capability == "no" || analyzer_override.is_some();
        let render_positions =
            options.positions && (capability == "no" || capability.contains("positions"));
        let render_offsets =
            options.offsets && (capability == "no" || capability.contains("offsets"));
        let Some(field) = state.fields.get(&mapping.name) else {
            continue;
        };
        let source_path = mapping
            .multi_field_source
            .as_ref()
            .map(|source| source.path.as_str())
            .unwrap_or(&mapping.name);
        let mut texts = Vec::new();
        for value in source_values_for_tantivy_field_path(&document.source, source_path) {
            collect_positioned_text_values(value, &mut texts);
        }
        if texts.is_empty() {
            continue;
        }
        let analyzed = analyze_positioned_texts_with_override(
            &state.index,
            field.field,
            &texts,
            field
                .text_position_gap
                .unwrap_or(if mapping.field_type == TantivyFieldType::Keyword {
                    0
                } else {
                    100
                }),
            analyzer_override,
        )?;
        let mut tokens = BTreeMap::<String, Vec<tantivy::tokenizer::Token>>::new();
        for token in analyzed.tokens {
            tokens.entry(token.text.clone()).or_default().push(token);
        }
        let inverted = state
            .searcher
            .segment_reader(address.segment_ord)
            .inverted_index(field.field)
            .map_err(tantivy_error)?;
        let mut terms = serde_json::Map::new();
        for (text, analyzed_tokens) in tokens {
            let term = Term::from_field_text(field.field, &text);
            // Generated vectors describe native analysis of this document, independently
            // of the search index's stored frequency/position capabilities.
            let mut positions = Vec::new();
            let frequency = if generated {
                if render_positions {
                    positions.extend(analyzed_tokens.iter().map(|token| token.position as u32));
                }
                analyzed_tokens.len()
            } else {
                let Some(mut postings) = inverted
                    .read_postings(&term, IndexRecordOption::WithFreqsAndPositions)
                    .map_err(tantivy_error)?
                else {
                    continue;
                };
                if postings.seek(address.doc_id) != address.doc_id {
                    continue;
                }
                if render_positions {
                    postings.positions(&mut positions);
                }
                postings.term_freq() as usize
            };
            let mut value = serde_json::json!({"term_freq": frequency});
            if render_positions || render_offsets {
                if analyzed_tokens.len() != frequency
                    || (render_positions && positions.len() != analyzed_tokens.len())
                {
                    return Err(invalid_request("native term frequency/analysis mismatch"));
                }
                let mut rendered = Vec::with_capacity(analyzed_tokens.len());
                for (ordinal, token) in analyzed_tokens.iter().enumerate() {
                    let mut token_value = serde_json::Map::new();
                    if render_positions {
                        token_value.insert("position".into(), Value::from(positions[ordinal]));
                    }
                    if render_offsets {
                        // Tantivy analyzes byte offsets; the REST contract counts UTF-16 code units.
                        let start = analyzed.text.get(..token.offset_from).ok_or_else(|| {
                            invalid_request("native token start offset is invalid")
                        })?;
                        let end = analyzed
                            .text
                            .get(..token.offset_to)
                            .ok_or_else(|| invalid_request("native token end offset is invalid"))?;
                        token_value.insert(
                            "start_offset".into(),
                            Value::from(start.encode_utf16().count()),
                        );
                        token_value
                            .insert("end_offset".into(), Value::from(end.encode_utf16().count()));
                    }
                    rendered.push(Value::Object(token_value));
                }
                value["tokens"] = Value::Array(rendered);
            }
            if options.term_statistics {
                let mut doc_freq = 0u64;
                let mut ttf = 0u64;
                for segment in state.searcher.segment_readers() {
                    let inverted = segment.inverted_index(field.field).map_err(tantivy_error)?;
                    if let Some(info) = inverted.get_term_info(&term).map_err(tantivy_error)? {
                        doc_freq += u64::from(info.doc_freq);
                        let mut postings = inverted
                            .read_postings_from_terminfo(&info, IndexRecordOption::WithFreqs)
                            .map_err(tantivy_error)?;
                        while postings.doc() != tantivy::TERMINATED {
                            ttf += u64::from(postings.term_freq());
                            postings.advance();
                        }
                    }
                }
                value["doc_freq"] = Value::from(doc_freq);
                value["ttf"] = Value::from(ttf);
            }
            terms.insert(text, value);
        }
        if terms.is_empty() {
            continue;
        }
        let mut result = serde_json::json!({"terms": terms});
        if options.field_statistics {
            result["field_statistics"] =
                state.termvector_field_statistics.read(state, field.field)?;
        }
        fields.insert(mapping.name.clone(), result);
    }
    Ok(NativeTermVectorResponse {
        document: GetDocumentResponse {
            index: request.index,
            metadata: document.metadata.clone(),
            source: document.source.clone(),
            found: true,
        },
        fields,
    })
}
