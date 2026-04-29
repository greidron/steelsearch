//! Source-owned restore validation helpers for stale/corrupt/incompatible snapshot metadata.

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SnapshotRestoreValidationFailure {
    StaleMetadata,
    CorruptMetadata,
    IncompatibleMetadata,
}

pub fn snapshot_restore_validation_reason(
    failure: SnapshotRestoreValidationFailure,
) -> &'static str {
    match failure {
        SnapshotRestoreValidationFailure::StaleMetadata => {
            "stale snapshot metadata rejected before restore"
        }
        SnapshotRestoreValidationFailure::CorruptMetadata => {
            "corrupt snapshot metadata rejected before restore"
        }
        SnapshotRestoreValidationFailure::IncompatibleMetadata => {
            "incompatible snapshot metadata rejected before restore"
        }
    }
}

pub fn build_snapshot_restore_validation_failure(
    failure: SnapshotRestoreValidationFailure,
) -> serde_json::Value {
    serde_json::json!({
        "error": {
            "type": "snapshot_restore_exception",
            "reason": snapshot_restore_validation_reason(failure)
        },
        "status": 400
    })
}

pub fn validate_snapshot_restore_metadata(
    metadata: &serde_json::Value,
) -> Result<(), SnapshotRestoreValidationFailure> {
    let Some(object) = metadata.as_object() else {
        return Err(SnapshotRestoreValidationFailure::CorruptMetadata);
    };

    if object.get("stale").and_then(serde_json::Value::as_bool) == Some(true) {
        return Err(SnapshotRestoreValidationFailure::StaleMetadata);
    }
    if object.get("corrupt").and_then(serde_json::Value::as_bool) == Some(true) {
        return Err(SnapshotRestoreValidationFailure::CorruptMetadata);
    }
    if object
        .get("incompatible")
        .and_then(serde_json::Value::as_bool)
        == Some(true)
    {
        return Err(SnapshotRestoreValidationFailure::IncompatibleMetadata);
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stale_metadata_rejected_with_snapshot_restore_exception() {
        let error = build_snapshot_restore_validation_failure(
            SnapshotRestoreValidationFailure::StaleMetadata,
        );

        assert_eq!(error["error"]["type"], "snapshot_restore_exception");
        assert_eq!(
            error["error"]["reason"],
            "stale snapshot metadata rejected before restore"
        );
        assert_eq!(error["status"], 400);
    }

    #[test]
    fn corrupt_and_incompatible_flags_map_to_distinct_failure_classes() {
        assert_eq!(
            validate_snapshot_restore_metadata(&serde_json::json!({
                "corrupt": true
            })),
            Err(SnapshotRestoreValidationFailure::CorruptMetadata)
        );
        assert_eq!(
            validate_snapshot_restore_metadata(&serde_json::json!({
                "incompatible": true
            })),
            Err(SnapshotRestoreValidationFailure::IncompatibleMetadata)
        );
    }

    #[test]
    fn clean_metadata_passes_validation() {
        assert_eq!(
            validate_snapshot_restore_metadata(&serde_json::json!({
                "snapshot": "snapshot-a",
                "repository": "repo-a"
            })),
            Ok(())
        );
    }
}
