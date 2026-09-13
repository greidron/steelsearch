//! Diagnostic prototype only; does not change runtime lookup or establish a performance gate.
use std::hint::black_box;
use std::time::Instant;

#[path = "../crates/os-engine-tantivy/src/field_cache.rs"]
mod field_cache;
use field_cache::FieldCache;

fn hinted_get<'a, T>(cache: &'a FieldCache<T>, key: &str, hint: &mut usize) -> Option<&'a T> {
    match cache {
        FieldCache::Small(fields) => {
            // A position is never trusted across documents without checking its exact key.
            if let Some((name, value)) = fields.get(*hint) {
                if name == key {
                    return Some(value);
                }
            }
            let found = fields.iter().position(|(name, _)| name == key);
            *hint = found.unwrap_or(usize::MAX);
            found.map(|position| &fields[position].1)
        }
        FieldCache::Tree(fields) => fields.get(key),
    }
}

fn corpus(width: usize, varying: bool) -> Vec<FieldCache<String>> {
    (0..5000).map(|document| {
        (0..width).filter(|field| !varying || (document + field) % 13 != 0)
            .map(|field| (format!("field-{field:04}"), format!("value-{document}-{field}")))
            .collect()
    }).collect()
}

fn queries(width: usize) -> Vec<String> {
    [0, 1, width / 2, width.saturating_sub(1)].into_iter()
        .map(|field| format!("field-{field:04}"))
        .chain([String::from("absent")]).collect()
}

fn verify(caches: &[FieldCache<String>], keys: &[String]) {
    let mut hints = vec![usize::MAX; keys.len()];
    for cache in caches {
        for (key, hint) in keys.iter().zip(&mut hints) {
            assert_eq!(hinted_get(cache, key, hint), cache.get(key));
        }
    }
}

fn measure(caches: &[FieldCache<String>], keys: &[String], hinted: bool) -> (u128, usize) {
    let mut hints = vec![usize::MAX; keys.len()];
    let start = Instant::now();
    let mut checksum = 0;
    for _ in 0..16 {
        for cache in caches {
            for (key, hint) in keys.iter().zip(&mut hints) {
                let value = if hinted {
                    hinted_get(black_box(cache), black_box(key), hint)
                } else {
                    black_box(cache).get(black_box(key))
                };
                checksum += black_box(value).map_or(0, String::len);
            }
        }
    }
    (start.elapsed().as_nanos(), checksum)
}

fn main() {
    println!("width,varying,round,variant,elapsed_ns,checksum");
    if std::env::args().any(|arg| arg == "--facet-strings") {
        // String cache shape from run-http-load-baseline.py::document_for.
        let names = ["category", "event_time", "message", "service", "status", "tenant", "title"];
        for varying in [false, true] {
            let caches = (0..5000).map(|document| {
                names.iter().enumerate()
                    .filter(|(field, _)| !varying || (document + field) % 13 != 0)
                    .map(|(field, name)| (name.to_string(), format!("value-{document}-{field}")))
                    .collect::<FieldCache<_>>()
            }).collect::<Vec<_>>();
            let keys = ["category", "service"].into_iter().map(str::to_owned).collect::<Vec<_>>();
            verify(&caches, &keys);
            let mut expected = None;
            for round in 0..8 {
                let hinted = matches!(round % 4, 1 | 2);
                let (elapsed, checksum) = measure(&caches, &keys, hinted);
                assert_eq!(*expected.get_or_insert(checksum), checksum);
                println!("7,{varying},{round},{},{elapsed},{checksum}",
                    if hinted { "hinted" } else { "current" });
            }
        }
        return;
    }
    for width in [0, 1, 3, 8, 9, 16, 64, 256] {
        for varying in [false, true] {
            let caches = corpus(width, varying);
            let keys = queries(width);
            verify(&caches, &keys);
            let mut expected = None;
            // Two predeclared ABBA blocks; retain every measurement.
            for round in 0..8 {
                let hinted = matches!(round % 4, 1 | 2);
                let (elapsed, checksum) = measure(&caches, &keys, hinted);
                assert_eq!(*expected.get_or_insert(checksum), checksum);
                println!("{width},{varying},{round},{},{elapsed},{checksum}",
                    if hinted { "hinted" } else { "current" });
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;

    #[test]
    fn stale_positions_and_changing_keys_never_return_another_field() {
        let keys = ["", "a", "a\0", "\0", "\u{00e9}", "a.b", "ab", "abc", "abcd", "abcde"];
        for count in 0..=keys.len() {
            let input = keys[..count].iter().enumerate()
                .map(|(value, key)| (key.to_string(), value)).collect::<Vec<_>>();
            let expected = input.iter().cloned().collect::<BTreeMap<_, _>>();
            let cache = input.into_iter().collect::<FieldCache<_>>();
            for initial in [0, 1, 7, 8, 64, usize::MAX] {
                let mut hint = initial;
                for key in keys.iter().copied().chain(["missing", "a.b.c"]).cycle().take(48) {
                    assert_eq!(hinted_get(&cache, key, &mut hint), expected.get(key));
                }
            }
        }
    }

    #[test]
    fn field_presence_type_and_container_changes_preserve_lookup() {
        let key = "field-0007";
        let mut hint = usize::MAX;
        for width in [8, 0, 9, 1, 64, 8, 7, 8] {
            for missing in [false, true] {
                let input = (0..width).filter(|i| !missing || *i != 7)
                    .map(|i| (format!("field-{i:04}"), i as f64)).collect::<Vec<_>>();
                let expected = input.iter().cloned().collect::<BTreeMap<_, _>>();
                let cache = input.into_iter().collect::<FieldCache<_>>();
                assert_eq!(hinted_get(&cache, key, &mut hint), expected.get(key));
            }
        }
    }
}
