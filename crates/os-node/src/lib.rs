//! Node lifecycle scaffolding.

pub mod development_runtime;
pub mod allocation_explain_route_registration;
pub mod alias_read_route_registration;
pub mod alias_mutation_route_registration;
pub mod bulk_route_registration;
pub mod cluster_state_route_registration;
pub mod cluster_settings_route_registration;
pub mod create_index_route_registration;
pub mod data_stream_route_registration;
pub mod delete_index_route_registration;
pub mod get_index_route_registration;
pub mod single_doc_delete_route_registration;
pub mod single_doc_get_route_registration;
pub mod single_doc_update_route_registration;
pub mod head_index_route_registration;
pub mod legacy_template_route_registration;
pub mod mapping_route_registration;
pub mod optimistic_concurrency_semantics;
pub mod pending_tasks_route_registration;
pub mod refresh_policy_semantics;
pub mod rollover_route_registration;
pub mod routing_semantics;
pub mod settings_route_registration;
pub mod snapshot_repository_route_registration;
pub mod snapshot_lifecycle_route_registration;
pub mod snapshot_cleanup_route_registration;
pub mod single_doc_post_route_registration;
pub mod single_doc_put_route_registration;
pub mod snapshot_restore_validation;
pub mod stats_route_registration;
pub mod tasks_route_registration;
pub mod template_route_registration;
pub mod write_path_invariants;

use os_core::Version;
pub use development_runtime::*;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NodeInfo {
    pub name: String,
    pub version: Version,
}
