//! Source-owned optimistic concurrency subset for Phase A write-path work.

pub const OPTIMISTIC_CONCURRENCY_FIELDS: [&str; 2] = ["if_seq_no", "if_primary_term"];
pub const VERSION_CONFLICT_ERROR_TYPE: &str = "version_conflict_engine_exception";

pub fn build_optimistic_concurrency_subset(query: &serde_json::Value) -> serde_json::Value {
    let Some(object) = query.as_object() else {
        return serde_json::json!({});
    };

    let mut subset = serde_json::Map::new();
    for field in OPTIMISTIC_CONCURRENCY_FIELDS {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn optimistic_concurrency_matches(
    expected_seq_no: Option<i64>,
    expected_primary_term: Option<i64>,
    actual_seq_no: i64,
    actual_primary_term: i64,
) -> bool {
    match (expected_seq_no, expected_primary_term) {
        (Some(seq_no), Some(primary_term)) => {
            seq_no == actual_seq_no && primary_term == actual_primary_term
        }
        _ => true,
    }
}

pub fn build_version_conflict_error(index: &str, id: &str) -> serde_json::Value {
    serde_json::json!({
        "error": {
            "type": VERSION_CONFLICT_ERROR_TYPE,
            "reason": format!("[{id}]: version conflict in index [{index}]")
        },
        "status": 409
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn optimistic_concurrency_subset_keeps_only_seq_no_and_primary_term() {
        let subset = build_optimistic_concurrency_subset(&serde_json::json!({
            "if_seq_no": 7,
            "if_primary_term": 3,
            "routing": "tenant-a"
        }));

        assert_eq!(
            subset,
            serde_json::json!({
                "if_seq_no": 7,
                "if_primary_term": 3
            })
        );
    }

    #[test]
    fn optimistic_concurrency_match_requires_both_fields_when_present() {
        assert!(optimistic_concurrency_matches(Some(7), Some(3), 7, 3));
        assert!(!optimistic_concurrency_matches(Some(7), Some(3), 8, 3));
        assert!(!optimistic_concurrency_matches(Some(7), Some(3), 7, 4));
        assert!(optimistic_concurrency_matches(None, None, 7, 3));
    }

    #[test]
    fn version_conflict_error_keeps_bounded_conflict_class() {
        let error = build_version_conflict_error("logs-000001", "doc-1");
        assert_eq!(
            error["error"]["type"],
            serde_json::json!(VERSION_CONFLICT_ERROR_TYPE)
        );
        assert_eq!(error["status"], serde_json::json!(409));
    }
}
