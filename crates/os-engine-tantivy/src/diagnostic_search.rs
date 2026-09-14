//! Search-phase timing samples for local diagnosis only.
//!
//! This module is excluded from ordinary and release builds. It deliberately
//! writes sparse samples to stderr instead of changing the public metrics API.

use std::io::Write;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;

const SAMPLE_EVERY: u64 = 256;

pub(crate) struct Site {
    name: &'static str,
    attempts: AtomicU64,
}

impl Site {
    pub(crate) const fn new(name: &'static str) -> Self {
        Self {
            name,
            attempts: AtomicU64::new(0),
        }
    }
}

pub(crate) static SHARDED_QUERY_BUILD: Site = Site::new("sharded_query_build");
pub(crate) static SHARDED_TANTIVY_SEARCH: Site = Site::new("sharded_tantivy_search");
pub(crate) static SHARDED_HIT_MATERIALIZATION: Site =
    Site::new("sharded_hit_materialization");
pub(crate) static SHARDED_PAGE: Site = Site::new("sharded_page");
pub(crate) static SHARDED_PAGE_CANDIDATE_COLLECTION: Site =
    Site::new("sharded_page_candidate_collection");
pub(crate) static SHARDED_PAGE_SORT: Site = Site::new("sharded_page_sort");
pub(crate) static SHARDED_PAGE_RESPONSE_BUILD: Site =
    Site::new("sharded_page_response_build");
pub(crate) static SHARDED_CANDIDATE_SETUP: Site = Site::new("sharded_candidate_setup");
pub(crate) static SHARDED_CANDIDATE_FANOUT: Site = Site::new("sharded_candidate_fanout");
pub(crate) static SHARDED_CANDIDATE_REDUCE: Site = Site::new("sharded_candidate_reduce");
pub(crate) static NATIVE_BM25_WEIGHT: Site = Site::new("native_bm25_weight");
pub(crate) static NATIVE_BM25_FIELD_STATISTICS: Site =
    Site::new("native_bm25_field_statistics");
pub(crate) static NATIVE_BM25_GENERATION_CHECK: Site =
    Site::new("native_bm25_generation_check");
pub(crate) static NATIVE_BM25_TANTIVY_WEIGHT: Site =
    Site::new("native_bm25_tantivy_weight");
pub(crate) static ENGINE_SEARCH: Site = Site::new("engine_search");
pub(crate) static ENGINE_PLAIN_SNAPSHOT: Site = Site::new("engine_plain_snapshot");
pub(crate) static ENGINE_PLAIN_EXECUTE: Site = Site::new("engine_plain_execute");
pub(crate) static NATIVE_PHRASE_POSITION_MATCH: Site =
    Site::new("native_phrase_position_match");
pub(crate) static NATIVE_PHRASE_WEIGHT: Site = Site::new("native_phrase_weight");
pub(crate) static NATIVE_PHRASE_SCORER: Site = Site::new("native_phrase_scorer");
pub(crate) static NATIVE_PHRASE_FIND_MATCH: Site = Site::new("native_phrase_find_match");

pub(crate) struct Span {
    site: &'static str,
    attempt: u64,
    started: Option<Instant>,
}

pub(crate) fn start(site: &Site) -> Span {
    let attempt = site.attempts.fetch_add(1, Ordering::Relaxed);
    Span {
        site: site.name,
        attempt,
        started: (attempt % SAMPLE_EVERY == 0).then(Instant::now),
    }
}

impl Drop for Span {
    fn drop(&mut self) {
        let Some(started) = self.started.take() else {
            return;
        };
        let _ = writeln!(
            std::io::stderr().lock(),
            "STEELSEARCH_SEARCH_DIAGNOSTIC {{\"site\":\"{}\",\"pid\":{},\"attempt\":{},\"sample_every\":{},\"elapsed_ns\":{}}}",
            self.site,
            std::process::id(),
            self.attempt,
            SAMPLE_EVERY,
            started.elapsed().as_nanos(),
        );
    }
}
