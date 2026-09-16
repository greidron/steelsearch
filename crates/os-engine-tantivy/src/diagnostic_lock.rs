//! Sampled diagnostic timings only; this module is absent from default builds.

use std::io::Write;
use std::ops::{Deref, DerefMut};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;

const SAMPLE_EVERY: u64 = 64;

pub(crate) struct Site {
    name: &'static str,
    attempts: AtomicU64,
}

impl Site {
    const fn new(name: &'static str) -> Self {
        Self {
            name,
            attempts: AtomicU64::new(0),
        }
    }
}

pub(crate) static SEARCH_SNAPSHOT: Site = Site::new("search_snapshot");
pub(crate) static VECTOR_UNCACHED_READ: Site = Site::new("vector_uncached_read");
pub(crate) static REFRESH_PLAN: Site = Site::new("refresh_plan");
pub(crate) static REFRESH_PUBLISH: Site = Site::new("refresh_publish");
pub(crate) static REFRESH_OWNER: Site = Site::new("refresh_owner");

pub(crate) struct TimedGuard<G> {
    guard: Option<G>,
    sample: Option<Sample>,
}

struct Sample {
    site: &'static str,
    attempt: u64,
    wait_ns: u128,
    acquired: Instant,
}

pub(crate) fn acquire<G>(site: &Site, lock: impl FnOnce() -> G) -> TimedGuard<G> {
    let attempt = site.attempts.fetch_add(1, Ordering::Relaxed);
    let start = (attempt % SAMPLE_EVERY == 0).then(Instant::now);
    let guard = lock();
    let sample = start.map(|started| {
        let acquired = Instant::now();
        Sample {
            site: site.name,
            attempt,
            wait_ns: acquired.duration_since(started).as_nanos(),
            acquired,
        }
    });
    TimedGuard {
        guard: Some(guard),
        sample,
    }
}

impl<G: Deref> Deref for TimedGuard<G> {
    type Target = G::Target;
    fn deref(&self) -> &Self::Target {
        self.guard.as_ref().expect("live diagnostic guard").deref()
    }
}

impl<G: DerefMut> DerefMut for TimedGuard<G> {
    fn deref_mut(&mut self) -> &mut Self::Target {
        self.guard
            .as_mut()
            .expect("live diagnostic guard")
            .deref_mut()
    }
}

impl<G> TimedGuard<G> {
    fn release(&mut self) -> Option<(Sample, u128)> {
        let held_ns = self
            .sample
            .as_ref()
            .map(|sample| sample.acquired.elapsed().as_nanos());
        // Release the observed lock before taking stderr's lock or doing I/O.
        drop(self.guard.take());
        self.sample.take().zip(held_ns)
    }
}

impl<G> Drop for TimedGuard<G> {
    fn drop(&mut self) {
        if let Some((sample, held_ns)) = self.release() {
            let _ = writeln!(std::io::stderr().lock(),
                "STEELSEARCH_LOCK_DIAGNOSTIC {{\"site\":\"{}\",\"pid\":{},\"attempt\":{},\"sample_every\":{},\"wait_ns\":{},\"held_ns\":{}}}",
                sample.site, std::process::id(), sample.attempt, SAMPLE_EVERY,
                sample.wait_ns, held_ns);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    #[test]
    fn sample_schedule_and_mutation_preserve_lock_behavior() {
        let site = Site::new("test");
        let lock = Mutex::new(0);
        for attempt in 0..130 {
            let mut guard = acquire(&site, || lock.lock().unwrap());
            assert_eq!(guard.sample.is_some(), attempt % SAMPLE_EVERY == 0);
            assert!(lock.try_lock().is_err());
            *guard += 1;
            let sample = guard.release();
            assert!(lock.try_lock().is_ok());
            if let Some((sample, _)) = sample {
                assert_eq!(sample.attempt, attempt);
            }
        }
        assert_eq!(*lock.lock().unwrap(), 130);
    }

    #[test]
    fn early_return_drops_underlying_guard() {
        let lock = Mutex::new(0);
        let site = Site::new("test");
        let run = || {
            let _guard = acquire(&site, || lock.lock().unwrap());
            Err::<(), _>("early")?;
            Ok::<(), &str>(())
        };
        assert!(run().is_err());
        assert!(lock.try_lock().is_ok());
    }

    #[test]
    fn acquisition_failure_preserves_poisoning() {
        let lock = Mutex::new(0);
        let site = Site::new("test");
        let _ = std::panic::catch_unwind(|| {
            let _guard = lock.lock().unwrap();
            panic!("poison");
        });
        assert!(std::panic::catch_unwind(|| acquire(&site, || lock.lock().unwrap())).is_err());
        assert!(lock.is_poisoned());
    }
}
