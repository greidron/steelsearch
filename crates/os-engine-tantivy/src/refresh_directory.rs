use std::io;
use std::path::Path;
use std::sync::{Arc, Condvar, Mutex};
use std::time::{Duration, Instant};

use tantivy::directory::error::{DeleteError, LockError, OpenReadError, OpenWriteError};
use tantivy::directory::{
    Directory, DirectoryLock, FileHandle, Lock, RamDirectory, WatchCallback, WatchHandle, WritePtr,
};

#[derive(Clone, Debug)]
pub(crate) struct RefreshDirectory {
    inner: RamDirectory,
    wake: Arc<(Mutex<()>, Condvar)>,
}

impl Default for RefreshDirectory {
    fn default() -> Self {
        Self {
            inner: RamDirectory::create(),
            wake: Arc::new((Mutex::new(()), Condvar::new())),
        }
    }
}

struct NotifyingLock {
    inner: Option<DirectoryLock>,
    wake: Arc<(Mutex<()>, Condvar)>,
}

impl Drop for NotifyingLock {
    fn drop(&mut self) {
        let _guard = self
            .wake
            .0
            .lock()
            .expect("RAM directory wake mutex poisoned");
        drop(self.inner.take());
        self.wake.1.notify_all();
    }
}

impl RefreshDirectory {
    pub(crate) fn fork_committed(&self) -> tantivy::Result<Self> {
        use tantivy::directory::{INDEX_WRITER_LOCK, META_LOCK};
        let _guard = self.acquire_lock(&META_LOCK)?;
        let inner = self.inner.deep_clone();
        // Lock markers belong to the original directory, not its independent copy.
        for lock in [&*INDEX_WRITER_LOCK, &*META_LOCK] {
            if inner.exists(&lock.filepath)? {
                inner
                    .delete(&lock.filepath)
                    .map_err(|error| io::Error::other(error.to_string()))?;
            }
        }
        Ok(Self {
            inner,
            wake: Arc::new((Mutex::new(()), Condvar::new())),
        })
    }

    fn acquire_with_timeout(
        &self,
        lock: &Lock,
        timeout: Duration,
    ) -> Result<DirectoryLock, LockError> {
        let started = Instant::now();
        let nonblocking = Lock {
            filepath: lock.filepath.clone(),
            is_blocking: false,
        };
        let mut guard = self
            .wake
            .0
            .lock()
            .expect("RAM directory wake mutex poisoned");
        loop {
            match self.inner.acquire_lock(&nonblocking) {
                Ok(inner) => {
                    return Ok(DirectoryLock::from(Box::new(NotifyingLock {
                        inner: Some(inner),
                        wake: Arc::clone(&self.wake),
                    })))
                }
                Err(LockError::LockBusy) if lock.is_blocking => {
                    let remaining = timeout.saturating_sub(started.elapsed());
                    if remaining.is_zero() {
                        return Err(LockError::LockBusy);
                    }
                    // Share the mutex with unlock so a release cannot race the start of waiting.
                    guard = self
                        .wake
                        .1
                        .wait_timeout(guard, remaining)
                        .expect("RAM directory wake mutex poisoned")
                        .0;
                }
                Err(error) => return Err(error),
            }
        }
    }
}

impl Directory for RefreshDirectory {
    fn get_file_handle(&self, path: &Path) -> Result<Arc<dyn FileHandle>, OpenReadError> {
        self.inner.get_file_handle(path)
    }
    fn delete(&self, path: &Path) -> Result<(), DeleteError> {
        self.inner.delete(path)
    }
    fn exists(&self, path: &Path) -> Result<bool, OpenReadError> {
        self.inner.exists(path)
    }
    fn open_write(&self, path: &Path) -> Result<WritePtr, OpenWriteError> {
        self.inner.open_write(path)
    }
    fn atomic_read(&self, path: &Path) -> Result<Vec<u8>, OpenReadError> {
        self.inner.atomic_read(path)
    }
    fn atomic_write(&self, path: &Path, data: &[u8]) -> io::Result<()> {
        self.inner.atomic_write(path, data)
    }
    fn sync_directory(&self) -> io::Result<()> {
        self.inner.sync_directory()
    }
    fn watch(&self, callback: WatchCallback) -> tantivy::Result<WatchHandle> {
        self.inner.watch(callback)
    }
    fn acquire_lock(&self, lock: &Lock) -> Result<DirectoryLock, LockError> {
        // Tantivy's default blocking file-lock policy waits up to 100 * 100ms.
        self.acquire_with_timeout(lock, Duration::from_secs(10))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    fn lock(blocking: bool) -> Lock {
        Lock {
            filepath: ".test.lock".into(),
            is_blocking: blocking,
        }
    }

    #[test]
    fn clones_share_nonblocking_exclusion_and_release() {
        let directory = RefreshDirectory::default();
        let held = directory.acquire_lock(&lock(false)).unwrap();
        assert!(matches!(
            directory.clone().acquire_lock(&lock(false)),
            Err(LockError::LockBusy)
        ));
        let other = Lock {
            filepath: ".other.lock".into(),
            is_blocking: false,
        };
        let independent = directory.clone().acquire_lock(&other).unwrap();
        assert!(directory.exists(&lock(false).filepath).unwrap());
        drop(held);
        assert!(!directory.exists(&lock(false).filepath).unwrap());
        assert!(directory.clone().acquire_lock(&lock(false)).is_ok());
        drop(independent);
    }

    #[test]
    fn blocking_timeout_does_not_remove_another_holders_lock() {
        let directory = RefreshDirectory::default();
        let held = directory.acquire_lock(&lock(false)).unwrap();
        assert!(matches!(
            directory.acquire_with_timeout(&lock(true), Duration::from_millis(5)),
            Err(LockError::LockBusy)
        ));
        assert!(directory.exists(&lock(false).filepath).unwrap());
        drop(held);
        assert!(directory.acquire_lock(&lock(false)).is_ok());
    }

    #[test]
    fn concurrent_waiters_never_overlap_and_all_finish() {
        let directory = RefreshDirectory::default();
        let active = AtomicUsize::new(0);
        let completed = AtomicUsize::new(0);
        std::thread::scope(|scope| {
            for _ in 0..8 {
                let (directory, active, completed) = (directory.clone(), &active, &completed);
                scope.spawn(move || {
                    for _ in 0..64 {
                        let held = directory.acquire_lock(&lock(true)).unwrap();
                        assert_eq!(active.fetch_add(1, Ordering::SeqCst), 0);
                        std::thread::yield_now();
                        assert_eq!(active.fetch_sub(1, Ordering::SeqCst), 1);
                        completed.fetch_add(1, Ordering::SeqCst);
                        drop(held);
                    }
                });
            }
        });
        assert_eq!(completed.load(Ordering::SeqCst), 512);
        assert_eq!(active.load(Ordering::SeqCst), 0);
    }
}
