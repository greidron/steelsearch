use tantivy::merge_policy::{LogMergePolicy, MergePolicy};
use tantivy::schema::Schema;
use tantivy::{Index, SegmentId, SegmentMeta};

fn smaller_floor_policy() -> LogMergePolicy {
    let mut policy = LogMergePolicy::default();
    policy.set_min_layer_size(512);
    policy
}

#[test]
fn log_merge_policy_distinguishes_seed_from_small_refreshes() {
    let index = Index::create_in_ram(Schema::builder().build());
    let seed = index.new_segment_meta(SegmentId::generate_random(), 1667);
    let mut segments = vec![seed.clone()];
    segments.extend((0..8).map(|_| index.new_segment_meta(SegmentId::generate_random(), 4)));
    let original = LogMergePolicy::default().compute_merge_candidates(&segments);
    assert_eq!(original.len(), 1);
    assert!(original[0].0.contains(&seed.id()));
    let adjusted = smaller_floor_policy().compute_merge_candidates(&segments);
    assert_eq!(adjusted.len(), 1);
    assert_eq!(adjusted[0].0.len(), 8);
    assert!(!adjusted[0].0.contains(&seed.id()));
}

#[derive(Debug)]
struct ModelStats {
    rewritten_documents: u64,
    merge_count: usize,
    max_settled_segments: usize,
}

fn model_refreshes(policy: &dyn MergePolicy, seed_docs: u32, batch_docs: u32) -> ModelStats {
    let index = Index::create_in_ram(Schema::builder().build());
    let mut segments = vec![index.new_segment_meta(SegmentId::generate_random(), seed_docs)];
    let mut stats = ModelStats { rewritten_documents: 0, merge_count: 0, max_settled_segments: 1 };
    // This is a metadata work model, not asynchronous execution or a latency benchmark.
    for batch in 0..768 {
        segments.push(index.new_segment_meta(SegmentId::generate_random(), batch_docs));
        loop {
            let merges = policy.compute_merge_candidates(&segments);
            if merges.is_empty() {
                break;
            }
            for merge in merges {
                assert!(merge.0.len() >= 2);
                let merged_docs: u32 = segments.iter().filter(|s| merge.0.contains(&s.id()))
                    .map(SegmentMeta::num_docs).sum();
                stats.rewritten_documents += u64::from(merged_docs);
                stats.merge_count += 1;
                segments.retain(|s| !merge.0.contains(&s.id()));
                segments.push(index.new_segment_meta(SegmentId::generate_random(), merged_docs));
            }
        }
        assert_eq!(segments.iter().map(SegmentMeta::num_docs).sum::<u32>(),
            seed_docs + (batch + 1) * batch_docs);
        stats.max_settled_segments = stats.max_settled_segments.max(segments.len());
    }
    stats
}

#[test]
fn lower_merge_floor_bounds_settled_segments_and_reduces_modeled_rewrites() {
    for seed_docs in [1000, 1667, 5000] {
        for batch_docs in [1, 4, 16] {
            let original = model_refreshes(&LogMergePolicy::default(), seed_docs, batch_docs);
            let adjusted = model_refreshes(&smaller_floor_policy(), seed_docs, batch_docs);
            eprintln!("metadata model seed={seed_docs} batch={batch_docs}: default={original:?}, floor512={adjusted:?}");
            assert!(adjusted.rewritten_documents * 2 < original.rewritten_documents);
            assert!(adjusted.merge_count > 0);
            assert!(adjusted.max_settled_segments <= 64);
        }
    }
}

#[test]
fn lower_merge_floor_preserves_numeric_values_deletes_and_old_readers() {
    use tantivy::collector::{Count, DocSetCollector};
    use tantivy::query::{AllQuery, TermQuery};
    use tantivy::schema::{IndexRecordOption, NumericOptions, STORED, STRING};
    use tantivy::{Document, IndexReader, ReloadPolicy, Term};

    let mut schema = Schema::builder();
    let id_field = schema.add_text_field("_id", STRING | STORED);
    let number_field = schema.add_f64_field("numbers", NumericOptions::default().set_indexed().set_fast());
    let index = Index::create_in_ram(schema.build());
    let mut writer = index.writer_with_num_threads(1, 16 * 1024 * 1024).unwrap();
    writer.set_merge_policy(Box::new(smaller_floor_policy()));
    let reader: IndexReader = index.reader_builder().reload_policy(ReloadPolicy::Manual).try_into().unwrap();
    let document = |id: u32| {
        let mut document = Document::default();
        document.add_text(id_field, &format!("doc-{id}"));
        for offset in 0..32 {
            document.add_f64(number_field, f64::from(id * 64 + offset) + 0.25);
        }
        document
    };
    for id in 0..1024 {
        writer.add_document(document(id)).unwrap();
    }
    writer.commit().unwrap();
    reader.reload().unwrap();
    let old_searcher = reader.searcher();
    for batch in 0..24 {
        for id in 1024 + batch * 4..1024 + (batch + 1) * 4 {
            writer.add_document(document(id)).unwrap();
        }
        writer.commit().unwrap();
        reader.reload().unwrap();
        assert_eq!(reader.searcher().search(&AllQuery, &Count).unwrap(), 1024 + (batch as usize + 1) * 4);
    }
    writer.delete_term(Term::from_field_text(id_field, "doc-0"));
    writer.commit().unwrap();
    writer.wait_merging_threads().unwrap();
    reader.reload().unwrap();
    let searcher = reader.searcher();
    let segment_sizes: Vec<_> = searcher.segment_readers().iter().map(|segment| segment.num_docs()).collect();
    eprintln!("actual floor512 settled segment sizes: {segment_sizes:?}");
    assert!(segment_sizes.len() <= 16);
    assert_eq!(searcher.search(&AllQuery, &Count).unwrap(), 1119);
    assert_eq!(old_searcher.search(&AllQuery, &Count).unwrap(), 1024);
    let deleted_value = TermQuery::new(Term::from_field_f64(number_field, 0.25), IndexRecordOption::Basic);
    assert_eq!(searcher.search(&deleted_value, &Count).unwrap(), 0);
    assert_eq!(old_searcher.search(&deleted_value, &Count).unwrap(), 1);
    let columns: Vec<_> = searcher.segment_readers().iter()
        .map(|segment| segment.fast_fields().f64("numbers").unwrap()).collect();
    for address in searcher.search(&AllQuery, &DocSetCollector).unwrap() {
        let stored: Document = searcher.doc(address).unwrap();
        let id: u32 = stored.get_first(id_field).unwrap().as_text().unwrap()
            .strip_prefix("doc-").unwrap().parse().unwrap();
        assert_ne!(id, 0);
        assert_eq!(stored.get_all(number_field).count(), 0);
        assert_eq!(columns[address.segment_ord as usize].values_for_doc(address.doc_id).collect::<Vec<_>>(),
            (0..32).map(|offset| f64::from(id * 64 + offset) + 0.25).collect::<Vec<_>>());
    }
}

#[test]
fn engine_refresh_merge_preserves_paging_across_shards_and_deletes() {
    use os_engine::{CreateIndexRequest, DeleteDocumentRequest, IndexDocumentRequest, IndexEngine, RefreshRequest};
    use os_engine_tantivy::TantivyEngine;
    use serde_json::json;

    for shards in [1, 3] {
        let engine = TantivyEngine::default();
        engine.create_index(CreateIndexRequest {
            index: "merge-pages".to_string(), settings: json!({"number_of_shards": shards}),
            mappings: json!({"properties": {"ordinal": {"type": "long"}, "numbers": {"type": "double"}}}),
        }).unwrap();
        let source = |id: usize| json!({"ordinal": id,
            "numbers": (0..16).map(|offset| (id * 32 + offset) as f64 + 0.25).collect::<Vec<_>>()});
        for id in 0..3168 {
            engine.index_document(IndexDocumentRequest {
                index: "merge-pages".to_string(), id: format!("doc-{id}"), source: source(id),
            }).unwrap();
            if id >= 3071 && (id + 1) % 4 == 0 {
                engine.refresh(RefreshRequest { indices: vec!["merge-pages".to_string()] }).unwrap();
            }
        }
        for deleted in [false, true] {
            if deleted {
                engine.delete_document(DeleteDocumentRequest {
                    index: "merge-pages".to_string(), id: "doc-0".to_string(),
                }).unwrap();
                engine.refresh(RefreshRequest { indices: vec!["merge-pages".to_string()] }).unwrap();
            }
            for from in [0, 3068, 3072, 3158] {
                let response = engine.search(serde_json::from_value(json!({
                    "indices": ["merge-pages"], "query": {"match_all": {}}, "aggregations": {},
                    "sort": [{"field": "ordinal", "order": "asc"}], "from": from, "size": 9
                })).unwrap()).unwrap();
                assert_eq!(response.total_hits, 3168 - u64::from(deleted));
                assert_eq!(response.hits.len(), 9);
                for (offset, hit) in response.hits.iter().enumerate() {
                    let id = from + offset + usize::from(deleted);
                    assert_eq!(hit.metadata.id, format!("doc-{id}"), "shards={shards}, from={from}");
                    assert_eq!(hit.source, source(id));
                    assert_eq!(hit.sort, Some(json!([id])));
                }
            }
        }
    }
}
