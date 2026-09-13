//! Diagnostic only: compare counting containers, not end-to-end search latency.
use std::collections::{BTreeMap, HashMap};
use std::hint::black_box;
use std::time::Instant;

fn tree<'a>(values: &[&'a str]) -> Vec<(&'a str, u64)> {
    let mut counts = BTreeMap::new();
    for value in values {
        *counts.entry(*value).or_insert(0) += 1;
    }
    let mut result = counts.into_iter().collect::<Vec<_>>();
    result.sort_unstable_by(|(a, n), (b, m)| m.cmp(n).then_with(|| a.cmp(b)));
    result
}

fn hash<'a>(values: &[&'a str]) -> Vec<(&'a str, u64)> {
    let mut counts = HashMap::new();
    for value in values {
        *counts.entry(*value).or_insert(0) += 1;
    }
    let mut result = counts.into_iter().collect::<Vec<_>>();
    result.sort_unstable_by(|(a, n), (b, m)| m.cmp(n).then_with(|| a.cmp(b)));
    result
}

fn hybrid<'a>(values: &[&'a str]) -> Vec<(&'a str, u64)> {
    enum Counts<'a> {
        Small(Vec<(&'a str, u64)>),
        Tree(BTreeMap<&'a str, u64>),
    }
    let mut counts = Counts::Small(Vec::new());
    for value in values {
        match &mut counts {
            Counts::Tree(tree) => *tree.entry(*value).or_insert(0) += 1,
            Counts::Small(small) => {
                if let Some((_, count)) = small.iter_mut().find(|(key, _)| key == value) {
                    *count += 1;
                } else if small.len() < 8 {
                    small.push((*value, 1));
                } else {
                    let mut tree = small.drain(..).collect::<BTreeMap<_, _>>();
                    tree.insert(*value, 1);
                    counts = Counts::Tree(tree);
                }
            }
        }
    }
    let mut result = match counts {
        Counts::Small(small) => small,
        Counts::Tree(tree) => tree.into_iter().collect(),
    };
    result.sort_unstable_by(|(a, n), (b, m)| m.cmp(n).then_with(|| a.cmp(b)));
    result
}

fn hybrid_split<'a>(values: &[&'a str]) -> Vec<(&'a str, u64)> {
    let mut small: Vec<(&str, u64)> = Vec::new();
    let mut remaining = values.iter();
    while let Some(value) = remaining.next() {
        if let Some((_, count)) = small.iter_mut().find(|(key, _)| key == value) {
            *count += 1;
        } else if small.len() < 8 {
            small.push((*value, 1));
        } else {
            let mut tree = small.into_iter().collect::<BTreeMap<_, _>>();
            tree.insert(*value, 1);
            for value in remaining {
                *tree.entry(*value).or_insert(0) += 1;
            }
            small = tree.into_iter().collect();
            break;
        }
    }
    small.sort_unstable_by(|(a, n), (b, m)| m.cmp(n).then_with(|| a.cmp(b)));
    small
}

fn term_tag(value: &str) -> u64 {
    let bytes = value.as_bytes();
    let suffix = &bytes[bytes.len().saturating_sub(8)..];
    let mut tag = [0; 8];
    tag[..suffix.len()].copy_from_slice(suffix);
    u64::from_ne_bytes(tag)
}

fn fingerprinted<'a>(values: &[&'a str]) -> Vec<(&'a str, u64)> {
    enum Counts<'a> {
        Small(Vec<(u64, &'a str, u64)>),
        Tree(BTreeMap<&'a str, u64>),
    }
    let mut counts = Counts::Small(Vec::new());
    for &value in values {
        match &mut counts {
            Counts::Tree(tree) => *tree.entry(value).or_insert(0) += 1,
            Counts::Small(small) => {
                let tag = term_tag(value);
                if let Some((_, _, count)) = small.iter_mut().find(|(cached, key, _)| {
                    *cached == tag
                        && key.len() == value.len()
                        && (value.len() <= 8 || *key == value)
                }) {
                    *count += 1;
                } else if small.len() < 8 {
                    small.push((tag, value, 1));
                } else {
                    let mut tree = small
                        .drain(..)
                        .map(|(_, key, count)| (key, count))
                        .collect::<BTreeMap<_, _>>();
                    tree.insert(value, 1);
                    counts = Counts::Tree(tree);
                }
            }
        }
    }
    let mut result = match counts {
        Counts::Small(small) => small
            .into_iter()
            .map(|(_, key, count)| (key, count))
            .collect::<Vec<_>>(),
        Counts::Tree(tree) => tree.into_iter().collect(),
    };
    result.sort_unstable_by(|(a, n), (b, m)| m.cmp(n).then_with(|| a.cmp(b)));
    result
}

fn length_tree<'a>(values: &[&'a str]) -> Vec<(&'a str, u64)> {
    #[derive(Eq, PartialEq)]
    struct Key<'a>(&'a str);
    impl Ord for Key<'_> {
        fn cmp(&self, other: &Self) -> std::cmp::Ordering {
            self.0
                .len()
                .cmp(&other.0.len())
                .then_with(|| self.0.cmp(other.0))
        }
    }
    impl PartialOrd for Key<'_> {
        fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
            Some(self.cmp(other))
        }
    }
    let mut counts = BTreeMap::new();
    for value in values {
        *counts.entry(Key(value)).or_insert(0) += 1;
    }
    let mut result = counts
        .into_iter()
        .map(|(key, count)| (key.0, count))
        .collect::<Vec<_>>();
    result.sort_unstable_by(|(a, n), (b, m)| m.cmp(n).then_with(|| a.cmp(b)));
    result
}

fn main() {
    for keys in [
        vec![
            "",
            "\0",
            "\0\0",
            "a",
            "a\0",
            "12345678",
            "\u{00e9}",
            "\u{00e9}\0",
        ],
        vec!["x12345678", "y12345678", "z12345678"],
    ] {
        let values = (0..5000).map(|i| keys[i % keys.len()]).collect::<Vec<_>>();
        assert_eq!(tree(&values), fingerprinted(&values));
    }
    println!("cardinality,round,container,elapsed_ns");
    for cardinality in [1, 3, 8, 9, 32, 1024] {
        let keys = if cardinality == 3 {
            ["commerce", "search", "analytics"]
                .into_iter()
                .map(str::to_owned)
                .collect::<Vec<_>>()
        } else {
            (0..cardinality)
                .map(|i| format!("category-{i:04}"))
                .collect::<Vec<_>>()
        };
        // Documents own distinct allocations even when their term contents are equal.
        let owned_values = (0..5000)
            .map(|i| keys[(i * 17) % cardinality].clone())
            .collect::<Vec<_>>();
        let values = owned_values.iter().map(String::as_str).collect::<Vec<_>>();
        assert_eq!(tree(&values), hash(&values));
        assert_eq!(tree(&values), hybrid(&values));
        assert_eq!(tree(&values), hybrid_split(&values));
        assert_eq!(tree(&values), length_tree(&values));
        assert_eq!(tree(&values), fingerprinted(&values));
        for round in 0..4 {
            for variant in if round % 2 == 0 {
                ["tree", "hash", "hybrid", "split", "length", "tag"]
            } else {
                ["tag", "length", "split", "hybrid", "hash", "tree"]
            } {
                let start = Instant::now();
                for _ in 0..500 {
                    black_box(match variant {
                        "tree" => tree(black_box(&values)),
                        "hash" => hash(black_box(&values)),
                        "hybrid" => hybrid(black_box(&values)),
                        "split" => hybrid_split(black_box(&values)),
                        "tag" => fingerprinted(black_box(&values)),
                        _ => length_tree(black_box(&values)),
                    });
                }
                println!(
                    "{cardinality},{round},{variant},{}",
                    start.elapsed().as_nanos()
                );
            }
        }
    }
}
