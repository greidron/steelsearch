//! Isolated dictionary construction diagnostic, not an HTTP performance gate.
use std::alloc::{GlobalAlloc, Layout, System};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;

use serde::Serialize;
use tantivy::directory::FileSlice;
use tantivy::postings::TermInfo;
use tantivy::termdict::{TermDictionary, TermDictionaryBuilder};

static ALLOCATIONS: AtomicU64 = AtomicU64::new(0);
static REQUESTED: AtomicU64 = AtomicU64::new(0);
static LIVE: AtomicU64 = AtomicU64::new(0);
static PEAK: AtomicU64 = AtomicU64::new(0);

struct CountingAllocator;

fn record_allocation(bytes: usize) {
    ALLOCATIONS.fetch_add(1, Ordering::Relaxed);
    REQUESTED.fetch_add(bytes as u64, Ordering::Relaxed);
    let live = LIVE.fetch_add(bytes as u64, Ordering::Relaxed) + bytes as u64;
    PEAK.fetch_max(live, Ordering::Relaxed);
}

// Forward the exact allocation contracts to System; accounting never allocates.
unsafe impl GlobalAlloc for CountingAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let pointer = unsafe { System.alloc(layout) };
        if !pointer.is_null() {
            record_allocation(layout.size());
        }
        pointer
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        let pointer = unsafe { System.alloc_zeroed(layout) };
        if !pointer.is_null() {
            record_allocation(layout.size());
        }
        pointer
    }
    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        unsafe { System.dealloc(pointer, layout) };
        LIVE.fetch_sub(layout.size() as u64, Ordering::Relaxed);
    }
    unsafe fn realloc(&self, pointer: *mut u8, layout: Layout, size: usize) -> *mut u8 {
        let resized = unsafe { System.realloc(pointer, layout, size) };
        if !resized.is_null() {
            LIVE.fetch_sub(layout.size() as u64, Ordering::Relaxed);
            record_allocation(size);
        }
        resized
    }
}

#[global_allocator]
static ALLOCATOR: CountingAllocator = CountingAllocator;

#[derive(Serialize)]
struct Stage {
    elapsed_ns: u64,
    allocations: u64,
    requested_bytes: u64,
    live_delta_bytes: i64,
    extra_peak_bytes: u64,
}

fn measure<T>(operation: impl FnOnce() -> T) -> (T, Stage) {
    let allocations = ALLOCATIONS.load(Ordering::Relaxed);
    let requested = REQUESTED.load(Ordering::Relaxed);
    let live = LIVE.load(Ordering::Relaxed);
    PEAK.store(live, Ordering::Relaxed);
    let started = Instant::now();
    let output = operation();
    let elapsed_ns = started.elapsed().as_nanos() as u64;
    let stage = Stage {
        elapsed_ns,
        allocations: ALLOCATIONS.load(Ordering::Relaxed) - allocations,
        requested_bytes: REQUESTED.load(Ordering::Relaxed) - requested,
        live_delta_bytes: LIVE.load(Ordering::Relaxed) as i64 - live as i64,
        extra_peak_bytes: PEAK.load(Ordering::Relaxed).saturating_sub(live),
    };
    (output, stage)
}

fn keys(shape: &str, count: usize) -> Vec<Vec<u8>> {
    let mut keys: Vec<_> = (0..count as u64)
        .map(|id| match shape {
            "numeric" => id.to_be_bytes().to_vec(),
            "prefix" => format!("shared/category/term-{id:012}/suffix").into_bytes(),
            "spread" => {
                let mut bytes = id.wrapping_mul(0x9e3779b97f4a7c15).to_be_bytes().to_vec();
                bytes.extend_from_slice(&id.to_be_bytes());
                bytes
            }
            _ => panic!("unknown key shape"),
        })
        .collect();
    keys.sort_unstable();
    assert!(keys.windows(2).all(|pair| pair[0] < pair[1]));
    keys
}

fn info(ordinal: usize) -> TermInfo {
    TermInfo {
        doc_freq: (ordinal % 31 + 1) as u32,
        postings_range: ordinal * 7..(ordinal + 1) * 7,
        positions_range: ordinal * 11..(ordinal + 1) * 11,
    }
}

fn validate(bytes: Vec<u8>, keys: &[Vec<u8>]) {
    let dictionary = TermDictionary::open(FileSlice::from(bytes)).unwrap();
    assert_eq!(dictionary.num_terms(), keys.len());
    let mut stream = dictionary.stream().unwrap();
    let mut restored = Vec::new();
    for (ordinal, key) in keys.iter().enumerate() {
        assert_eq!(dictionary.get(key).unwrap(), Some(info(ordinal)));
        assert_eq!(dictionary.term_ord(key).unwrap(), Some(ordinal as u64));
        assert!(dictionary
            .ord_to_term(ordinal as u64, &mut restored)
            .unwrap());
        assert_eq!(&restored, key);
        assert!(stream.advance());
        assert_eq!(stream.key(), key);
        assert_eq!(stream.value(), &info(ordinal));
    }
    assert!(!stream.advance());
    assert!(!dictionary
        .ord_to_term(keys.len() as u64, &mut restored)
        .unwrap());
    assert_eq!(dictionary.get(&[255; 64]).unwrap(), None);
    if keys.len() >= 4 {
        let (from, to) = (keys.len() / 4, keys.len() * 3 / 4);
        let mut range = dictionary
            .range()
            .ge(&keys[from])
            .lt(&keys[to])
            .into_stream()
            .unwrap();
        for (ordinal, key) in keys.iter().enumerate().take(to).skip(from) {
            assert!(range.advance());
            assert_eq!(range.key(), key);
            assert_eq!(range.value(), &info(ordinal));
        }
        assert!(!range.advance());
    }
}

fn run(round: usize, shape: &str, count: usize, dump_directory: Option<&Path>) {
    let keys = keys(shape, count);
    let repetitions = match count {
        0..=64 => 64,
        65..=1000 => 16,
        1001..=10000 => 4,
        _ => 2,
    };
    let mut samples = Vec::new();
    for repetition in 0..repetitions {
        let (mut builder, create) = measure(|| TermDictionaryBuilder::create(Vec::new()).unwrap());
        let (_, insert) = measure(|| {
            for (ordinal, key) in keys.iter().enumerate() {
                builder.insert(key, &info(ordinal)).unwrap();
            }
        });
        let (bytes, finish) = measure(|| builder.finish().unwrap());
        let dictionary_bytes = bytes.len();
        if repetition == 0 {
            if let Some(directory) = dump_directory {
                let path = directory.join(format!("{round}-{shape}-{count}.bin"));
                std::fs::OpenOptions::new()
                    .write(true)
                    .create_new(true)
                    .open(path)
                    .unwrap()
                    .write_all(&bytes)
                    .unwrap();
            }
        }
        validate(bytes, &keys);
        samples.push(
            serde_json::json!({"create": create, "insert": insert, "finish": finish,
            "dictionary_bytes": dictionary_bytes}),
        );
    }
    println!(
        "{}",
        serde_json::json!({"diagnostic_only": true, "acceptance_established": false,
        "allocator": "instrumented System, not server mimalloc", "round": round, "shape": shape,
        "terms": count, "repetitions": repetitions, "samples": samples,
        "limitations": "single-thread synthetic dictionaries; atomic allocation accounting adds overhead; requested bytes include full realloc requests, not RSS; validation and key generation excluded from stage timings; not an HTTP gate"})
    );
}

fn main() {
    let args: Vec<_> = std::env::args().skip(1).collect();
    let dump_directory = match args.as_slice() {
        [] => None,
        [flag, path] if flag == "--dictionary-output-dir" => Some(PathBuf::from(path)),
        _ => panic!("expected optional --dictionary-output-dir PATH"),
    };
    if let Some(directory) = &dump_directory {
        std::fs::create_dir(directory).unwrap();
    }
    for round in 0..2 {
        let mut counts = vec![0, 1, 4, 16, 64, 384, 1000, 10000, 100000];
        if round == 1 {
            counts.reverse();
        }
        for count in counts {
            for shape in ["numeric", "prefix", "spread"] {
                run(round, shape, count, dump_directory.as_deref());
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dictionary_shapes_preserve_entries_and_ranges() {
        for shape in ["numeric", "prefix", "spread"] {
            for count in [0, 1, 4, 257] {
                let keys = keys(shape, count);
                let mut builder = TermDictionaryBuilder::create(Vec::new()).unwrap();
                for (ordinal, key) in keys.iter().enumerate() {
                    builder.insert(key, &info(ordinal)).unwrap();
                }
                validate(builder.finish().unwrap(), &keys);
            }
        }
    }
}
