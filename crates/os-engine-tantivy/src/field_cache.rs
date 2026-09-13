use std::collections::BTreeMap;

#[derive(Clone, Debug, PartialEq)]
pub(crate) enum FieldCache<T> {
    Small(Vec<(String, T)>),
    Tree(Box<BTreeMap<String, T>>),
}

impl<T> Default for FieldCache<T> {
    fn default() -> Self {
        Self::Small(Vec::new())
    }
}

impl<T> FieldCache<T> {
    pub(crate) fn get_with_hint(&self, field: &str, hint: &mut usize) -> Option<&T> {
        match self {
            Self::Small(fields) => {
                // Documents can have different fields; a previous position is only a hint.
                if let Some((key, value)) = fields.get(*hint) {
                    if key == field {
                        return Some(value);
                    }
                }
                let position = fields.iter().position(|(key, _)| key == field);
                *hint = position.unwrap_or(usize::MAX);
                position.map(|index| &fields[index].1)
            }
            Self::Tree(fields) => fields.get(field),
        }
    }

    pub(crate) fn get(&self, field: &str) -> Option<&T> {
        match self {
            Self::Small(fields) => fields
                .iter()
                .find(|(key, _)| key == field)
                .map(|(_, value)| value),
            Self::Tree(fields) => fields.get(field),
        }
    }
}

impl<T> FromIterator<(String, T)> for FieldCache<T> {
    fn from_iter<I: IntoIterator<Item = (String, T)>>(iter: I) -> Self {
        let mut fields = iter.into_iter().collect::<Vec<_>>();
        if fields.len() > 8 {
            let tree = fields.into_iter().collect::<BTreeMap<_, _>>();
            return if tree.len() <= 8 {
                Self::Small(tree.into_iter().collect())
            } else {
                Self::Tree(Box::new(tree))
            };
        }
        // Stable order plus replacement retains the last value for duplicate keys.
        fields.sort_by(|a, b| a.0.cmp(&b.0));
        fields.dedup_by(|later, earlier| {
            if later.0 == earlier.0 {
                std::mem::swap(&mut later.1, &mut earlier.1);
                true
            } else {
                false
            }
        });
        Self::Small(fields)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lookup_hints_validate_keys_across_documents_and_container_transitions() {
        let keys = ["", "a", "a\0", "\0", "\u{00e9}", "a.b", "ab", "abc", "abcd", "abcde"];
        for initial in [0, 1, 7, 8, 64, usize::MAX] {
            let mut hint = initial;
            for size in [8, 0, 9, 1, 10, 7, 8] {
                for missing in [false, true] {
                    let tree = keys[..size].iter().enumerate()
                        .filter(|(i, _)| !missing || i % 2 == 0)
                        .map(|(i, key)| (key.to_string(), i)).collect::<BTreeMap<_, _>>();
                    let cache = tree.clone().into_iter().collect::<FieldCache<_>>();
                    for key in keys.iter().copied().chain(["missing", "a.b.c"]) {
                        assert_eq!(cache.get_with_hint(key, &mut hint), tree.get(key));
                    }
                }
            }
        }
    }

    #[test]
    fn cache_container_does_not_grow_document_fields() {
        assert!(std::mem::size_of::<FieldCache<String>>() <= std::mem::size_of::<BTreeMap<String, String>>());
        assert!(std::mem::size_of::<FieldCache<f64>>() <= std::mem::size_of::<BTreeMap<String, f64>>());
        assert!(std::mem::size_of::<FieldCache<i64>>() <= std::mem::size_of::<BTreeMap<String, i64>>());
    }

    #[test]
    fn exact_lookup_matches_tree_across_promotion_and_input_order() {
        let keys = ["", "a", "a\0", "\0", "\u{00e9}", "a.b", "ab", "abc", "abcd", "abcde"];
        for size in 0..=keys.len() {
            for reverse in [false, true] {
                let mut input = keys[..size].iter().enumerate()
                    .map(|(value, key)| (key.to_string(), value)).collect::<Vec<_>>();
                if reverse { input.reverse(); }
                let tree = input.iter().cloned().collect::<BTreeMap<_, _>>();
                let cache = input.into_iter().collect::<FieldCache<_>>();
                assert_eq!(matches!(cache, FieldCache::Small(_)), size <= 8);
                for key in keys.iter().copied().chain(["absent", "a.b.c"]) {
                    assert_eq!(cache.get(key), tree.get(key));
                }
                assert_eq!(cache.clone(), cache);
                assert_eq!(tree.into_iter().collect::<FieldCache<_>>(), cache);
            }
        }
    }

    #[test]
    fn duplicate_keys_keep_last_value_before_and_after_promotion() {
        for count in [1, 8, 9, 64] {
            let input = (0..count).map(|i| (format!("field-{i}"), i))
                .chain([(String::from("field-0"), 999)]).collect::<Vec<_>>();
            let tree = input.iter().cloned().collect::<BTreeMap<_, _>>();
            let cache = input.into_iter().collect::<FieldCache<_>>();
            for (key, value) in tree { assert_eq!(cache.get(&key), Some(&value)); }
        }
        assert_eq!(FieldCache::<i64>::default().get("missing"), None);
    }

    #[test]
    fn bulk_promotion_preserves_duplicates_in_remaining_iterator() {
        let input = (0..64).map(|i| (format!("field-{}", i % 12), i))
            .collect::<Vec<_>>();
        let expected = input.iter().cloned().collect::<BTreeMap<_, _>>();
        let cache = input.into_iter().collect::<FieldCache<_>>();
        assert!(matches!(cache, FieldCache::Tree(_)));
        for (key, value) in expected { assert_eq!(cache.get(&key), Some(&value)); }
    }

    #[test]
    fn duplicate_heavy_inputs_preserve_canonical_representation_and_owned_values() {
        for unique in [1, 2, 8, 9, 16] {
            for count in [1, 7, 8, 9, 17, 64] {
                let input = (0..count).map(|i| (format!("field-{}", i % unique), format!("value-{i}")))
                    .collect::<Vec<_>>();
                let tree = input.iter().cloned().collect::<BTreeMap<_, _>>();
                let cache = input.into_iter().collect::<FieldCache<_>>();
                assert_eq!(matches!(cache, FieldCache::Small(_)), tree.len() <= 8);
                let cloned = cache.clone();
                drop(cache);
                for (key, value) in &tree { assert_eq!(cloned.get(key), Some(value)); }
                assert_eq!(cloned, tree.into_iter().collect::<FieldCache<_>>());
            }
        }
    }
}
