//! HTTP and REST search timing samples for local diagnosis only.
//!
//! This module is excluded from ordinary and release builds. It emits sparse
//! stderr samples so the engine, REST route, and HTTP executor boundaries can
//! be separated without changing the public metrics API.

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

pub(crate) static HTTP_TOTAL: Site = Site::new("http_total");
pub(crate) static HTTP_BLOCKING_HANDLER_AND_ENCODE: Site =
    Site::new("http_blocking_handler_and_encode");
pub(crate) static SEARCH_ROUTE_TOTAL: Site = Site::new("search_route_total");
pub(crate) static SEARCH_NATIVE_DISPATCH: Site = Site::new("search_native_dispatch");
pub(crate) static NATIVE_RESPONSE_BUILD: Site = Site::new("native_response_build");

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
            "STEELSEARCH_NODE_SEARCH_DIAGNOSTIC {{\"site\":\"{}\",\"pid\":{},\"attempt\":{},\"sample_every\":{},\"elapsed_ns\":{}}}",
            self.site,
            std::process::id(),
            self.attempt,
            SAMPLE_EVERY,
            started.elapsed().as_nanos(),
        );
    }
}
