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
const BATCH: u32 = 4;
const REFRESHES: u32 = 256;
const VALUES: u32 = 384;

fn numeric_value(id: u32, offset: u32) -> f64 {
    // Same numeric distribution as tools/run-http-load-baseline.py::vector_for.
    f64::from(((id + 1) * 31 + offset * 17) % 1000) / 1000.0
}

fn run(floor: u32, indexed: bool, fast: bool, notified_locks: bool) {
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
    let directory: Box<dyn tantivy::Directory> = if notified_locks {
        Box::new(refresh_directory::RefreshDirectory::default())
    } else {
        Box::new(tantivy::directory::RamDirectory::create())
    };
    let index = Index::create(directory, schema.build(), Default::default()).unwrap();
    let mut writer = index.writer_with_num_threads(1, 16 * 1024 * 1024).unwrap();
    let mut policy = LogMergePolicy::default();
    policy.set_min_layer_size(floor);
    writer.set_merge_policy(Box::new(policy));
    let reader: IndexReader = index
        .reader_builder()
        .reload_policy(ReloadPolicy::Manual)
        .try_into()
        .unwrap();
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
    for batch in 0..REFRESHES {
        let started = Instant::now();
        for id in SEED + batch * BATCH..SEED + (batch + 1) * BATCH {
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
        assert_eq!(
            searcher.search(&AllQuery, &Count).unwrap(),
            (SEED + (batch + 1) * BATCH) as usize
        );
        samples.push(json!({"batch": batch, "add_ns": add_ns, "prepare_ns": prepare_ns,
            "publish_ns": publish_ns, "reload_ns": reload_ns,
            "segment_docs": searcher.segment_readers().iter().map(|s| s.num_docs()).collect::<Vec<_>>()}));
    }
    let started = Instant::now();
    writer.wait_merging_threads().unwrap();
    let merge_drain_ns = started.elapsed().as_nanos();
    reader.reload().unwrap();
    let searcher = reader.searcher();
    let expected = (SEED + REFRESHES * BATCH) as usize;
    assert_eq!(searcher.search(&AllQuery, &Count).unwrap(), expected);
    assert_eq!(
        old_searcher.search(&AllQuery, &Count).unwrap(),
        SEED as usize
    );
    let mut seen = vec![false; expected];
    for address in searcher.search(&AllQuery, &DocSetCollector).unwrap() {
        let stored: Document = searcher.doc(address).unwrap();
        let id: usize = stored
            .get_first(id_field)
            .unwrap()
            .as_text()
            .unwrap()
            .strip_prefix("doc-")
            .unwrap()
            .parse()
            .unwrap();
        assert!(id < expected && !seen[id]);
        seen[id] = true;
        assert_eq!(stored.get_all(number_field).count(), 0);
        if fast {
            let column = searcher
                .segment_reader(address.segment_ord)
                .fast_fields()
                .f64("numbers")
                .unwrap();
            assert_eq!(
                column.values_for_doc(address.doc_id).collect::<Vec<_>>(),
                (0..VALUES)
                    .map(|offset| numeric_value(id as u32, offset))
                    .collect::<Vec<_>>()
            );
        }
    }
    assert!(seen.iter().all(|found| *found));
    if indexed {
        for id in [0, SEED - 1, SEED, expected as u32 - 1] {
            for offset in [0, VALUES / 2, VALUES - 1] {
                let value = numeric_value(id, offset);
                let query = TermQuery::new(
                    Term::from_field_f64(number_field, value),
                    IndexRecordOption::Basic,
                );
                let expected_matches = (0..expected as u32)
                    .filter(|document_id| {
                        (0..VALUES).any(|position| numeric_value(*document_id, position) == value)
                    })
                    .count();
                assert_eq!(searcher.search(&query, &Count).unwrap(), expected_matches);
            }
        }
    }
    println!(
        "{}",
        json!({"diagnostic_only": true, "acceptance_established": false,
        "floor": floor, "indexed": indexed, "fast": fast, "seed": SEED,
        "notified_locks": notified_locks,
        "batch_docs": BATCH, "refreshes": REFRESHES, "numeric_values": VALUES,
        "limitations": "load-runner numeric distribution with sequential IDs; no HTTP, source fetch, concurrent load or engine routing; samples exclude validation and final merge drain; controls with disabled fields are not candidates",
        "merge_drain_ns": merge_drain_ns, "samples": samples,
        "final_segment_docs": searcher.segment_readers().iter().map(|s| s.num_docs()).collect::<Vec<_>>(),
        "validated_documents": expected})
    );
}

fn main() {
    let args: Vec<_> = std::env::args().skip(1).collect();
    let mut notified_locks = false;
    let mut indexed_fast_only = false;
    let mut selected_floor = None;
    for arg in args {
        match arg.as_str() {
            "--notified-locks" if !notified_locks => notified_locks = true,
            "--indexed-fast-only" if !indexed_fast_only => indexed_fast_only = true,
            _ if arg.starts_with("--floor=") && selected_floor.is_none() => {
                let floor: u32 = arg[8..].parse().expect("floor must be a positive u32");
                assert!(floor > 0, "floor must be positive");
                selected_floor = Some(floor);
            }
            _ => panic!("unknown or duplicate argument: {arg}"),
        }
    }
    let floors = selected_floor.map_or_else(
        || vec![10_000, 512, 512, 10_000],
        |floor| vec![floor, floor],
    );
    // Mirror the order to retain both observations, not a best-case selection.
    for floor in floors {
        for (indexed, fast) in [(true, true), (true, false), (false, true), (false, false)] {
            if indexed_fast_only && !(indexed && fast) {
                continue;
            }
            run(floor, indexed, fast, notified_locks);
        }
    }
}
