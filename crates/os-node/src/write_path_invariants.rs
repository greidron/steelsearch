//! Source-owned write-path invariant checklist for Phase A validation work.

pub const WRITE_PATH_INVARIANTS: [&str; 4] = [
    "replica_apply_path",
    "retry_safe_mapping_update",
    "durability_after_ack",
    "refresh_visibility_boundary",
];

pub fn requires_multi_node_validation(invariant: &str) -> bool {
    matches!(invariant, "replica_apply_path" | "durability_after_ack")
}

pub fn requires_retry_safe_mapping_validation(invariant: &str) -> bool {
    invariant == "retry_safe_mapping_update"
}

pub fn requires_explicit_refresh_boundary(invariant: &str) -> bool {
    invariant == "refresh_visibility_boundary"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn write_path_invariant_list_keeps_phase_a_validation_axes() {
        assert_eq!(
            WRITE_PATH_INVARIANTS,
            [
                "replica_apply_path",
                "retry_safe_mapping_update",
                "durability_after_ack",
                "refresh_visibility_boundary",
            ]
        );
    }

    #[test]
    fn write_path_invariant_helpers_split_multi_node_mapping_and_visibility_gates() {
        assert!(requires_multi_node_validation("replica_apply_path"));
        assert!(requires_multi_node_validation("durability_after_ack"));
        assert!(requires_retry_safe_mapping_validation(
            "retry_safe_mapping_update"
        ));
        assert!(requires_explicit_refresh_boundary(
            "refresh_visibility_boundary"
        ));
        assert!(!requires_multi_node_validation("refresh_visibility_boundary"));
    }
}
