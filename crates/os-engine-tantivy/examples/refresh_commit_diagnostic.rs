//! Opt-in isolated diagnostic; not an HTTP benchmark or implementation acceptance gate.
use std::time::Instant;

use serde_json::json;
use tantivy::collector::{Count, DocSetCollector};
use tantivy::merge_policy::LogMergePolicy;
use tantivy::query::{AllQuery, TermQuery};
use tantivy::schema::{IndexRecordOption, NumericOptions, Schema, STORED, STRING};
use tantivy::{Document, Index, IndexReader, ReloadPolicy, Term};

#[path = "../src/refresh_directory.rs"]
mod refresh_directory;

const SEED: u32 = 1667;
const DEFAULT_BATCH_DOCS: u32 = 4;
const DEFAULT_REFRESHES: u32 = 256;
const VALUES: u32 = 384;

#[derive(Debug, PartialEq, Eq)]
struct DiagnosticConfig {
    notified_locks: bool,
    indexed_fast_only: bool,
    selected_floor: Option<u32>,
    batch_docs: u32,
    refreshes: u32,
    final_documents: u32,
}

fn numeric_value(id: u32, offset: u32) -> f64 {
    // Same numeric distribution as tools/run-http-load-baseline.py::vector_for.
    (((u64::from(id) + 1) * 31 + u64::from(offset) * 17) % 1000) as f64 / 1000.0
}

fn run(floor: u32, config: &DiagnosticConfig, indexed: bool, fast: bool) {
    let mut schema = Schema::builder();
    let id_field = schema.add_text_field("_id", STRING | STORED);
    let mut options = NumericOptions::default();
    if indexed {
        options = options.set_indexed();
    }
    if fast {
        options = options.set_fast();
    }
    let number_field = schema.add_f64_field("numbers", options);
    let directory: Box<dyn tantivy::Directory> = if config.notified_locks {
        Box::new(refresh_directory::RefreshDirectory::default())
    } else {
        Box::new(tantivy::directory::RamDirectory::create())
    };
    let index = Index::create(directory, schema.build(), Default::default()).unwrap();
    let mut writer = index.writer_with_num_threads(1, 16 * 1024 * 1024).unwrap();
    let mut policy = LogMergePolicy::default();
    policy.set_min_layer_size(floor);
    writer.set_merge_policy(Box::new(policy));
    let reader: IndexReader = index.reader_builder().reload_policy(ReloadPolicy::Manual)
        .try_into().unwrap();
    let document = |id: u32| {
        let mut document = Document::default();
        document.add_text(id_field, &format!("doc-{id}"));
        for offset in 0..VALUES {
            document.add_f64(number_field, numeric_value(id, offset));
        }
        document
    };
    for id in 0..SEED {
        writer.add_document(document(id)).unwrap();
    }
    writer.commit().unwrap();
    reader.reload().unwrap();
    let old_searcher = reader.searcher();
    let mut samples = Vec::new();
    for batch in 0..config.refreshes {
        let started = Instant::now();
        for id in SEED + batch * config.batch_docs..SEED + (batch + 1) * config.batch_docs {
            writer.add_document(document(id)).unwrap();
        }
        let add_ns = started.elapsed().as_nanos();
        let started = Instant::now();
        let prepared = writer.prepare_commit().unwrap();
        let prepare_ns = started.elapsed().as_nanos();
        let started = Instant::now();
        prepared.commit().unwrap();
        let publish_ns = started.elapsed().as_nanos();
        let started = Instant::now();
        reader.reload().unwrap();
        let reload_ns = started.elapsed().as_nanos();
        let searcher = reader.searcher();
        assert_eq!(searcher.search(&AllQuery, &Count).unwrap(),
            (SEED + (batch + 1) * config.batch_docs) as usize);
        samples.push(json!({"batch": batch, "add_ns": add_ns, "prepare_ns": prepare_ns,
            "publish_ns": publish_ns, "reload_ns": reload_ns,
            "segment_docs": searcher.segment_readers().iter().map(|s| s.num_docs()).collect::<Vec<_>>()}));
    }
    let started = Instant::now();
    writer.wait_merging_threads().unwrap();
    let merge_drain_ns = started.elapsed().as_nanos();
    reader.reload().unwrap();
    let searcher = reader.searcher();
    let expected = config.final_documents as usize;
    assert_eq!(searcher.search(&AllQuery, &Count).unwrap(), expected);
    assert_eq!(old_searcher.search(&AllQuery, &Count).unwrap(), SEED as usize);
    let mut seen = vec![false; expected];
    for address in searcher.search(&AllQuery, &DocSetCollector).unwrap() {
        let stored: Document = searcher.doc(address).unwrap();
        let id: usize = stored.get_first(id_field).unwrap().as_text().unwrap()
            .strip_prefix("doc-").unwrap().parse().unwrap();
        assert!(id < expected && !seen[id]);
        seen[id] = true;
        assert_eq!(stored.get_all(number_field).count(), 0);
        if fast {
            let column = searcher.segment_reader(address.segment_ord).fast_fields().f64("numbers").unwrap();
            assert_eq!(column.values_for_doc(address.doc_id).collect::<Vec<_>>(),
                (0..VALUES).map(|offset| numeric_value(id as u32, offset)).collect::<Vec<_>>());
        }
    }
    assert!(seen.iter().all(|found| *found));
    if indexed {
        for id in [0, SEED - 1, SEED, expected as u32 - 1] {
            for offset in [0, VALUES / 2, VALUES - 1] {
                let value = numeric_value(id, offset);
                let query = TermQuery::new(Term::from_field_f64(number_field, value), IndexRecordOption::Basic);
                let expected_matches = (0..expected as u32).filter(|document_id|
                    (0..VALUES).any(|position| numeric_value(*document_id, position) == value)).count();
                assert_eq!(searcher.search(&query, &Count).unwrap(), expected_matches);
            }
        }
    }
    println!("{}", json!({"diagnostic_only": true, "acceptance_established": false,
        "floor": floor, "indexed": indexed, "fast": fast, "seed": SEED,
        "notified_locks": config.notified_locks,
        "batch_docs": config.batch_docs, "refreshes": config.refreshes, "numeric_values": VALUES,
        "limitations": "load-runner numeric distribution with sequential IDs; no HTTP, source fetch, concurrent load or engine routing; samples exclude validation and final merge drain; controls with disabled fields are not candidates",
        "merge_drain_ns": merge_drain_ns, "samples": samples,
        "final_segment_docs": searcher.segment_readers().iter().map(|s| s.num_docs()).collect::<Vec<_>>(),
        "validated_documents": expected}));
}

fn parse_args<I, S>(args: I) -> DiagnosticConfig
where
    I: IntoIterator<Item = S>,
    S: AsRef<str>,
{
    let mut notified_locks = false;
    let mut indexed_fast_only = false;
    let mut selected_floor = None;
    let mut batch_docs = None;
    let mut refreshes = None;
    for arg in args {
        let arg = arg.as_ref();
        match arg {
            "--notified-locks" if !notified_locks => notified_locks = true,
            "--indexed-fast-only" if !indexed_fast_only => indexed_fast_only = true,
            _ if arg.starts_with("--floor=") && selected_floor.is_none() => {
                let floor: u32 = arg[8..].parse().expect("floor must be a positive u32");
                assert!(floor > 0, "floor must be positive");
                selected_floor = Some(floor);
            }
            _ if arg.starts_with("--batch-docs=") && batch_docs.is_none() => {
                let value: u32 = arg[13..].parse().expect("batch docs must be a positive u32");
                assert!(value > 0, "batch docs must be positive");
                batch_docs = Some(value);
            }
            _ if arg.starts_with("--refreshes=") && refreshes.is_none() => {
                let value: u32 = arg[12..].parse().expect("refreshes must be a positive u32");
                assert!(value > 0, "refreshes must be positive");
                refreshes = Some(value);
            }
            _ => panic!("unknown or duplicate argument: {arg}"),
        }
    }
    let batch_docs = batch_docs.unwrap_or(DEFAULT_BATCH_DOCS);
    let refreshes = refreshes.unwrap_or(DEFAULT_REFRESHES);
    let added_documents = batch_docs.checked_mul(refreshes)
        .expect("batch docs multiplied by refreshes must fit in u32");
    let final_documents = SEED.checked_add(added_documents)
        .expect("seed plus batch docs multiplied by refreshes must fit in u32");
    DiagnosticConfig {
        notified_locks,
        indexed_fast_only,
        selected_floor,
        batch_docs,
        refreshes,
        final_documents,
    }
}

fn main() {
    let config = parse_args(std::env::args().skip(1));
    let floors = config.selected_floor.map_or_else(|| vec![10_000, 512, 512, 10_000],
        |floor| vec![floor, floor]);
    // Mirror the order to retain both observations, not a best-case selection.
    for floor in floors {
        for (indexed, fast) in [(true, true), (true, false), (false, true), (false, false)] {
            if config.indexed_fast_only && !(indexed && fast) { continue; }
            run(floor, &config, indexed, fast);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn numeric_distribution_does_not_wrap_for_large_document_ids() {
        assert_eq!(numeric_value(u32::MAX, 0), 0.176);
    }

    #[test]
    fn parse_args_uses_default_workload() {
        let config = parse_args([] as [&str; 0]);

        assert_eq!(config.batch_docs, DEFAULT_BATCH_DOCS);
        assert_eq!(config.refreshes, DEFAULT_REFRESHES);
        assert_eq!(config.final_documents, SEED + DEFAULT_BATCH_DOCS * DEFAULT_REFRESHES);
        assert!(!config.notified_locks);
        assert!(!config.indexed_fast_only);
        assert_eq!(config.selected_floor, None);
    }

    #[test]
    fn parse_args_accepts_explicit_workload_and_existing_flags() {
        let config = parse_args([
            "--batch-docs=7",
            "--refreshes=9",
            "--floor=512",
            "--notified-locks",
            "--indexed-fast-only",
        ]);

        assert_eq!(config.batch_docs, 7);
        assert_eq!(config.refreshes, 9);
        assert_eq!(config.final_documents, SEED + 63);
        assert_eq!(config.selected_floor, Some(512));
        assert!(config.notified_locks);
        assert!(config.indexed_fast_only);
    }

    #[test]
    #[should_panic(expected = "batch docs must be positive")]
    fn parse_args_rejects_zero_batch_docs() {
        parse_args(["--batch-docs=0"]);
    }

    #[test]
    #[should_panic(expected = "refreshes must be positive")]
    fn parse_args_rejects_zero_refreshes() {
        parse_args(["--refreshes=0"]);
    }

    #[test]
    #[should_panic(expected = "unknown or duplicate argument")]
    fn parse_args_rejects_duplicate_batch_docs() {
        parse_args(["--batch-docs=1", "--batch-docs=2"]);
    }

    #[test]
    #[should_panic(expected = "must fit in u32")]
    fn parse_args_rejects_overflowing_final_document_count() {
        parse_args(["--batch-docs=4294967295", "--refreshes=2"]);
    }
}
