//! Diagnostic only: immutable per-document field lookup, not a service performance gate.
use std::collections::{BTreeMap, HashMap};
use std::hint::black_box;
use std::time::Instant;

#[path = "../crates/os-engine-tantivy/src/field_cache.rs"]
mod field_cache;

#[allow(dead_code)]
enum CompactLayout<T> {
    Small(Vec<(String, T)>),
    Tree(Box<BTreeMap<String, T>>),
}

enum Cache {
    Tree(BTreeMap<String, String>),
    Sorted(Vec<(String, String)>),
    SmallLinear(Vec<(String, String)>),
    Hash(HashMap<String, String>),
    Adaptive(field_cache::FieldCache<String>),
}

impl Cache {
    fn new(kind: usize, fields: &[(String, String)]) -> Self {
        match kind {
            0 => Self::Tree(fields.iter().cloned().collect()),
            1 => Self::Sorted(fields.to_vec()),
            2 => Self::SmallLinear(fields.to_vec()),
            3 => Self::Hash(fields.iter().cloned().collect()),
            4 => Self::Adaptive(fields.iter().cloned().collect()),
            _ => unreachable!(),
        }
    }

    fn get(&self, key: &str) -> Option<&String> {
        match self {
            Self::Tree(fields) => fields.get(key),
            Self::Hash(fields) => fields.get(key),
            Self::Adaptive(fields) => fields.get(key),
            Self::SmallLinear(fields) if fields.len() <= 8 => {
                fields.iter().find(|(name, _)| name == key).map(|(_, value)| value)
            }
            Self::Sorted(fields) | Self::SmallLinear(fields) => fields
                .binary_search_by(|(name, _)| name.as_str().cmp(key))
                .ok()
                .map(|index| &fields[index].1),
        }
    }
}

fn corpus(field_count: usize, documents: usize) -> Vec<Vec<(String, String)>> {
    let names = ["category", "event_time", "message", "service", "tenant_id"];
    (0..documents)
        .map(|document| {
            let mut fields = (0..field_count)
                .filter(|field| (document + field) % 13 != 0)
                .map(|field| {
                    let key = if field < names.len() {
                        names[field].to_owned()
                    } else {
                        format!("shared_prefix_field_{field:04}")
                    };
                    (key, format!("value-{document}-{field}"))
                })
                .collect::<Vec<_>>();
            fields.sort_unstable_by(|a, b| a.0.cmp(&b.0));
            fields
        })
        .collect()
}

fn queries(field_count: usize) -> Vec<String> {
    ["category", "event_time", "message", "service", "tenant_id", "absent"]
        .into_iter()
        .map(str::to_owned)
        .chain([format!("shared_prefix_field_{:04}", field_count / 2),
            format!("shared_prefix_field_{:04}", field_count.saturating_sub(1))])
        .collect()
}

fn verify(caches: &[Cache], documents: &[Vec<(String, String)>], queries: &[String]) {
    for (cache, document) in caches.iter().zip(documents) {
        for query in queries {
            let expected = document.iter().find(|(key, _)| key == query).map(|(_, value)| value);
            assert_eq!(cache.get(query), expected);
        }
    }
}

fn main() {
    eprintln!("layout_bytes,string_tree={},string_adaptive={},f64_tree={},f64_adaptive={},i64_tree={},i64_adaptive={}",
        std::mem::size_of::<BTreeMap<String, String>>(),
        std::mem::size_of::<field_cache::FieldCache<String>>(),
        std::mem::size_of::<BTreeMap<String, f64>>(),
        std::mem::size_of::<field_cache::FieldCache<f64>>(),
        std::mem::size_of::<BTreeMap<String, i64>>(),
        std::mem::size_of::<field_cache::FieldCache<i64>>());
    eprintln!("compact_layout_bytes,string={},f64={},i64={}",
        std::mem::size_of::<CompactLayout<String>>(),
        std::mem::size_of::<CompactLayout<f64>>(),
        std::mem::size_of::<CompactLayout<i64>>());
    let names = ["tree", "sorted", "small_linear", "hash", "adaptive"];
    println!("field_count,round,container,build_ns,lookup_ns,checksum");
    for field_count in [0, 1, 3, 8, 9, 16, 64, 256] {
        let documents = corpus(field_count, 5000);
        let queries = queries(field_count);
        let mut expected = None;
        // Alternate order; allocate each container independently with owned document strings.
        for round in 0..4 {
            for position in 0..names.len() {
                let kind = if round % 2 == 0 { position } else { names.len() - 1 - position };
                let started = Instant::now();
                let caches = documents.iter().map(|fields| Cache::new(kind, fields)).collect::<Vec<_>>();
                let build_ns = started.elapsed().as_nanos();
                verify(&caches, &documents, &queries);
                let started = Instant::now();
                let mut checksum = 0usize;
                for iteration in 0..16 {
                    for (index, cache) in caches.iter().enumerate() {
                        let query = black_box(&queries[(index + iteration) % queries.len()]);
                        checksum += black_box(cache.get(query)).map_or(0, String::len);
                    }
                }
                let lookup_ns = started.elapsed().as_nanos();
                assert_eq!(*expected.get_or_insert(checksum), checksum);
                println!("{field_count},{round},{},{build_ns},{lookup_ns},{checksum}", names[kind]);
                black_box(caches);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_containers_preserve_exact_keys_and_missing_values() {
        let mut fields = ["", "a", "a\0", "\0", "\u{00e9}", "\u{00e9}\0", "a.b",
            "shared_prefix_field_0001", "shared_prefix_field_0002"]
            .into_iter().enumerate().map(|(i, key)| (key.to_owned(), i.to_string()))
            .collect::<Vec<_>>();
        fields.sort_unstable_by(|a, b| a.0.cmp(&b.0));
        for size in 0..=fields.len() {
            let documents = vec![fields[..size].to_vec()];
            let mut queries = fields.iter().map(|(key, _)| key.clone()).collect::<Vec<_>>();
            queries.extend(["missing".to_owned(), "a.b.c".to_owned()]);
            for kind in 0..5 {
                verify(&[Cache::new(kind, &documents[0])], &documents, &queries);
            }
        }
    }
}
