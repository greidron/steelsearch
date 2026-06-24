# Replacement Claim Exit Criteria

This document separates `REST parity complete` from `OpenSearch replacement
ready` and fixes the minimum evidence required for each replacement profile.

## REST Parity Complete Versus OpenSearch Replacement Ready

`REST parity complete` means a route family exists and the supported request,
response, error, and idempotency contract is covered by bounded standalone
evidence.

`OpenSearch replacement ready` means the relevant route families are present and
the target profile also has the durability, security, and distributed evidence
required for real replacement claims.

Promotion rule:

- Route presence alone is never enough for a replacement claim.
- The stronger claim requires every parity class listed below for the target
  profile.

## Parity Classes

| Parity class | Definition | Minimum evidence artifact family |
| --- | --- | --- |
| Route parity | Route registration, request envelope, status code, and response shape are OpenSearch-shaped for the supported subset. | generated route ledgers, OpenAPI artifacts, route compare fixtures |
| Semantic parity | Supported parameters, error paths, idempotency, selector expansion, and state transitions match the documented contract. | semantic and strict compat fixtures, stateful probe reports, targeted unit tests |
| Durability parity | Restart, replay, metadata persistence, manifest ownership, and on-disk compatibility are bounded and auditable. | restart smoke reports, durability compare reports, replay/manifest fixtures, on-disk policy docs |
| Security parity | Authn/authz, TLS, restricted-index access, and redaction guarantees are fixed for secure use. | security authz fixtures, security harness reports, redaction smoke, PKI/bootstrap policy fixtures |
| Distributed parity | Join, publication, allocation, recovery, replication, and mixed-failure behavior are bounded for interop or peer-node claims. | phase-B/phase-C harness reports, publication/allocation/recovery/replication schemas, mixed-cluster failure artifacts |

## Minimum Evidence By Parity Class

| Parity class | Minimum docs | Minimum fixtures / schemas | Minimum harness / report |
| --- | --- | --- | --- |
| Route parity | [README.md](/home/ubuntu/steelsearch/docs/api-spec/README.md), [source-compatibility-matrix.md](/home/ubuntu/steelsearch/docs/rust-port/source-compatibility-matrix.md) | route ledgers, route-specific compat fixtures | generated API spec artifact test and route compare report |
| Semantic parity | [search-parameter-coverage-matrix.md](/home/ubuntu/steelsearch/docs/api-spec/search-parameter-coverage-matrix.md), [document-write-semantic-gap-matrix.md](/home/ubuntu/steelsearch/docs/api-spec/document-write-semantic-gap-matrix.md), [snapshot-migration-semantic-gap-matrix.md](/home/ubuntu/steelsearch/docs/api-spec/snapshot-migration-semantic-gap-matrix.md) | semantic and strict compat fixtures, stateful probe ledgers | `tools/probe_stateful_route_ledger.py`, compat runner reports, route-family unit tests |
| Durability parity | [gateway-manifest-ownership.md](/home/ubuntu/steelsearch/docs/rust-port/gateway-manifest-ownership.md), [gateway-replay-recovery-policy.md](/home/ubuntu/steelsearch/docs/rust-port/gateway-replay-recovery-policy.md), [on-disk-state-upgrade-boundary.md](/home/ubuntu/steelsearch/docs/rust-port/on-disk-state-upgrade-boundary.md) | manifest/replay/durability fixtures | `tools/run-node-restart-smoke.sh`, `tools/run-durability-compat.sh` |
| Security parity | [security-role-route-matrix.md](/home/ubuntu/steelsearch/docs/api-spec/security-role-route-matrix.md), [restricted-index-prefix-inventory.md](/home/ubuntu/steelsearch/docs/api-spec/restricted-index-prefix-inventory.md), [security-redaction-baseline.md](/home/ubuntu/steelsearch/docs/api-spec/security-redaction-baseline.md) | `security-authz-compat.json`, PKI/bootstrap policy fixtures | `tools/run-security-compat-harness.sh`, `tools/check-security-redaction-smoke.sh` |
| Distributed parity | [phase-b-safe-interop.md](/home/ubuntu/steelsearch/docs/rust-port/phase-b-safe-interop.md), [phase-c-peer-node-compat.md](/home/ubuntu/steelsearch/docs/rust-port/phase-c-peer-node-compat.md) | handshake/cache/publication/allocation/recovery/replication schemas and transcript fixtures | `tools/run-phase-b-gap-harness.sh`, `tools/run-phase-c-gap-harness.sh` |

## Production Profile Readiness Checklists

### `standalone`

| Requirement type | Required items | Pass condition |
| --- | --- | --- |
| Required docs | route/semantic matrices, cutover runbook, snapshot/restore completeness matrix | Supported standalone surfaces are documented with explicit partial or fail-closed rules. |
| Required fixtures | search/document-write/snapshot semantic fixtures, startup preflight failures, restart smoke profiles | Representative happy-path and error-path fixtures exist for supported standalone routes. |
| Required harnesses | stateful route probe, migration acceptance harness, restart smoke, durability compare | Latest standalone reports complete without unresolved blocker rows for supported workflows. |
| Required pass conditions | route parity + semantic parity + durability parity | No unsupported or partial surface is silently treated as replacement-ready. |

### `secure standalone`

| Requirement type | Required items | Pass condition |
| --- | --- | --- |
| Required docs | standalone docs plus security role matrix, restricted-prefix inventory, redaction baseline | Security-sensitive route families have explicit minimum-role and deny-path policy. |
| Required fixtures | `security-authz-compat.json`, security bootstrap policy, PKI layout, restricted-index probes | Representative `401`, `403`, restricted-index, and redaction cases are fixed. |
| Required harnesses | security compat harness, redaction smoke, standalone restart and durability harnesses | Secure profile passes authn/authz and secret-handling checks in addition to standalone checks. |
| Required pass conditions | route parity + semantic parity + durability parity + security parity | Secure profile cannot be promoted while authn/authz or secret-handling remains stubbed. |

### `external interop`

| Requirement type | Required items | Pass condition |
| --- | --- | --- |
| Required docs | secure standalone docs when applicable plus handshake/version-skew matrix, stale-cache policy, interop allowlist | Every allowed and denied external interop action is explicitly classified. |
| Required fixtures | handshake reject cases, stale-cache reject cases, unsupported forwarded actions, mixed-mode transcripts | Version-skew and stale-cache failure paths are fixed with reject transcripts. |
| Required harnesses | `tools/run-phase-b-gap-harness.sh`, security harness where secure interop is claimed | Mixed-mode disconnect/publication/metadata failure profiles produce bounded fail-closed reports. |
| Required pass conditions | route parity + semantic parity + durability parity + distributed parity, plus security parity when secure | External interop cannot claim readiness while cache invalidation or unsupported forwarding remains ambiguous. |

### `same-cluster peer-node`

| Requirement type | Required items | Pass condition |
| --- | --- | --- |
| Required docs | interop docs plus join reject matrix, publication ordering matrix, allocation/relocation matrix, peer recovery matrix, replication matrix | Join/publication/recovery/replication lifecycle is documented as an auditable contract. |
| Required fixtures | join reject transcripts, publication/allocation/recovery/replication schemas, mixed-cluster failure profiles | Each mixed-cluster lifecycle has a report schema and representative failure artifact. |
| Required harnesses | `tools/run-phase-c-gap-harness.sh`, durability and restart harnesses, secure harnesses when claimed | Crash, stale replica, recovery interruption, and replication retry paths produce bounded reports. |
| Required pass conditions | all five parity classes | Peer-node readiness is blocked until the distributed lifecycle is evidenced end to end. |

## Go / No-Go Checklists

### Operator Go / No-Go

| Profile | Go only if | No-Go if |
| --- | --- | --- |
| `standalone` | Supported route families, migration acceptance, restart smoke, and durability compare all pass for the intended workload. | Any required cutover, restore, replay, or restart artifact is missing or failing. |
| `secure standalone` | Standalone checks pass and security harness plus redaction smoke pass with the intended credentials and TLS material. | Any authn/authz path, restricted-index policy, or redaction baseline is unresolved. |
| `external interop` | Secure checks pass when applicable and phase-B harness reports no unresolved fail-open behavior. | Handshake, version-skew, stale-cache, or unsupported forwarding remains undocumented or failing. |
| `same-cluster peer-node` | Phase-C lifecycle reports exist for join/publication/allocation/recovery/replication/failure and all required schemas are satisfied. | Any mixed-cluster lifecycle is only documented as planned or lacks bounded failure evidence. |

### Developer Go / No-Go

| Profile | Go only if | No-Go if |
| --- | --- | --- |
| `standalone` | Route rows are backed by semantic and durability artifacts, not only by API shape. | A route is marked `Partial` or `No` without a closing artifact plan. |
| `secure standalone` | Security-sensitive routes have explicit allow/deny fixtures and secure harness coverage. | Secure claims rely on stubbed security paths or undocumented credential policy. |
| `external interop` | Every forwarded or coordinated action is either on the allowlist or explicitly rejected. | A mixed-mode action can silently fall through, stale-cache reads can succeed, or version skew lacks a reject transcript. |
| `same-cluster peer-node` | Join, publication, allocation, recovery, replication, and crash paths each have schema-backed evidence. | Any peer-node capability is argued from route presence or documentation alone. |

## Compatibility Row Anchors

Use these anchors when mapping `Partial` or `No` rows from
[source-compatibility-matrix.md](/home/ubuntu/steelsearch/docs/rust-port/source-compatibility-matrix.md):

- `#area-root-and-basic-node-identity`
- `#area-cluster-health-state-allocation-and-node-stats`
- `#area-index-create-get-delete-and-mappings-settings`
- `#area-document-write-read-and-refresh`
- `#area-rest-bulk`
- `#area-rest-search`
- `#area-knn-vector-indexing-and-query-search`
- `#area-knn-plugin-rest-and-model-apis`
- `#area-ml-commons-neural-search-and-model-serving`
- `#area-snapshot-and-restore`
- `#area-migration-and-replacement-tooling`
- `#area-steelsearch-multi-node-runtime`
- `#area-native-transport-frame-and-opensearch-probe-compatibility`
- `#area-security-and-access-control`
- `#area-opensearch-comparison-harness`
- `#area-java-opensearch-data-node-compatibility`
- `#area-java-plugin-abi-compatibility`

## Area Backlog Map

### <a id="area-root-and-basic-node-identity"></a>Root and basic node identity

Standalone promotion is now allowed for this row.

Required gate:

- route parity:
  - `root-cluster-node-compat-report.json`
  - required case: `root_info`
- semantic parity:
  - `root-cluster-node-compat-report.json`
  - required case: `root_info`
- secure root auth envelope:
  - `security-authz-compat-report.json`
  - required cases:
    - `security_missing_root_info_401`
    - `security_bad_password_root_info_401`
    - `security_reader_root_info_success`

The replacement claim must treat both the non-secure root shape and the secure
root auth envelope as mandatory evidence. A stale or missing root route report
blocks promotion.

### <a id="area-cluster-health-state-allocation-and-node-stats"></a>Cluster health, state, allocation, and node stats

Standalone promotion is allowed only when the bounded admin route family and
the distributed-required field gate are both satisfied.

Required standalone route and semantic evidence:

- `cluster-health-compat-report.json`
- `allocation-explain-compat-report.json`
- `cluster-state-compat-report.json`
- `tasks-compat-report.json`
- `stats-compat-report.json`
- `search-compat-report.json` for `_cat/*`, representative `node_stats`, and
  pending-task shape readbacks

Required semantic cases:

- `cluster_health_wait_parameters`
- `cluster_health_wait_for_green_timeout_semantic`
- `cluster_health_wait_for_nodes_timeout_semantic`
- `cluster_state_readback`
- `cluster_pending_tasks_shape`
- `node_stats_shape`
- `allocation_explain_primary_happy_path`
- `allocation_explain_replica_unassigned_path`

Distributed-required fields must stay owned by the transport-admin gate instead
of the standalone route gate. Promotion is blocked if the allowlist boundary
between standalone-only fields and distributed-required fields drifts.

### <a id="area-index-create-get-delete-and-mappings-settings"></a>Index create/get/delete and mappings/settings

Standalone promotion is allowed only when template, alias, data-stream,
settings, and mapping evidence are aggregated as one route family and
restricted-target behavior remains explicitly owned by the secure gate.

Required standalone reports:

- `index-lifecycle-compat-report.json`
- `mapping-compat-report.json`
- `settings-compat-report.json`
- `alias-read-compat-report.json`
- `template-compat-report.json`
- `data-stream-rollover-compat-report.json`
- `search-compat-report.json` for wildcard/hidden/settings/template/alias/data
  stream representative readbacks

Required standalone cases:

- `get_component_template_readback`
- `get_index_template_readback`
- `templated_index_application_readback`
- `get_data_stream_metadata_readback`
- `get_data_stream_stats_readback`
- `delete_data_stream_ack`
- `dynamic_mapping_readback`
- `mapping_conflict_reject`
- `settings_targeted_named_readback`
- `settings_targeted_flat_readback`
- `settings_global_named_readback`
- `wildcard_index_read_visible_only`
- `settings_hidden_wildcard_put_ack`
- `settings_hidden_target_readback`
- `wildcard_alias_readback`
- `get_created_alias_readback`

Restricted, hidden, and wildcard security-sensitive behavior must not be
counted as standalone promotion evidence unless the following secure cases are
also present through `security-authz-compat-report.json`:

- `security_admin_restricted_index_get_success`
- `security_reader_restricted_index_get_403`
- `security_admin_restricted_settings_update_success`
- `security_writer_restricted_settings_update_403`
- `security_writer_restricted_delete_403`
- `security_admin_restricted_delete_success`
- `security_writer_restricted_create_403`
- `security_admin_restricted_create_success`

### <a id="area-document-write-read-and-refresh"></a>Document write/read and refresh

Standalone promotion is allowed only when single-document CRUD, routing,
refresh visibility, and durable multi-node propagation are all present in the
same gate.

Required standalone reports:

- `single-doc-crud-compat-report.json`
- `refresh-compat-report.json`
- `routing-compat-report.json`

Required semantic cases:

- `put_single_doc_explicit_id`
- `get_single_doc_filtered_source`
- `put_single_doc_external_version_success`
- `put_single_doc_external_version_conflict`
- `update_single_doc_optimistic_concurrency_success`
- `update_single_doc_optimistic_concurrency_conflict`
- `single_doc_routing_get_not_found`
- `single_doc_source_includes_readback`
- `single_doc_get_realtime_false_not_found`
- `single_doc_stored_fields_unsupported_error`
- `single_doc_put_lifecycle_get_not_found`
- `single_doc_create_refresh_false`
- `single_doc_get_realtime_false_after_refresh_false`
- `single_doc_create_refresh_wait_for`
- `single_doc_get_realtime_false_after_refresh_wait_for`
- `single_doc_create_refresh_true`
- `single_doc_get_realtime_false_after_refresh_true`

Required durability evidence:

- `multi-node-write-path-report.json`

Promotion is blocked if single-node write semantics are present without the
write-path durability and post-refresh visibility evidence.

### <a id="area-rest-bulk"></a>REST `_bulk`

Standalone promotion is allowed only when bulk metadata semantics, item-level
failure envelopes, secure authz behavior, and post-write durability are all
present in the same gate.

Required route evidence:

- `bulk-compat-report.json`

Required semantic cases:

- `global_bulk_optimistic_concurrency_success`
- `global_bulk_optimistic_concurrency_conflict`
- `global_bulk_auto_creates_missing_index`
- `global_bulk_create_into_data_stream_target`
- `global_bulk_partial_failure_item_shape`
- `global_bulk_refresh_pipeline_routing_shape`
- `get_bulk_routed_doc_after_wait_for_refresh`
- `global_bulk_external_version_create`
- `global_bulk_external_version_conflict`
- `index_scoped_bulk_default_target_update_upsert_shape`
- `bulk_routing_item_readback`
- `bulk_external_version_success_item`
- `bulk_external_version_conflict_item`
- `bulk_seq_term_success_item`
- `bulk_seq_term_conflict_item`
- `bulk_pipeline_metadata_unsupported_error`
- `bulk_version_without_external_policy_error`
- `bulk_item_ordering_partial_failure_matrix`
- `bulk_metadata_non_object_parse_error`
- `bulk_closed_index_item_failure_matrix`
- `bulk_refresh_false_readback_not_found`
- `bulk_refresh_true_readback`
- `bulk_refresh_wait_for_readback`
- `bulk_repeated_create_replay_conflict`

Required security cases through `security-authz-compat-report.json`:

- `security_writer_bulk_success`
- `security_admin_bulk_success`
- `security_reader_bulk_403`
- `security_writer_bulk_partial_authz_denial`

Required durability evidence:

- `multi-node-write-path-report.json`

Promotion is blocked if bulk route parity exists without the item-level authz
deny matrix or without replay/refresh durability evidence.

### <a id="area-rest-search"></a>REST `_search`

Standalone promotion is allowed only when supported DSL families, session
features, aggregation breadth, partial-failure handling, secure read behavior,
and unsupported-option fail-closed policy are all present in the same gate.

Required route evidence:

- `search-compat-report.json`

Required semantic cases:

- `exists_query_search`
- `validate_query_empty_search`
- `validate_query_target_rewrite_search`
- `prefix_query_search`
- `query_string_search`
- `query_string_url_q_overrides_body_search`
- `count_query_string_url_q_search`
- `render_template_named_search`
- `search_template_named_target_search`
- `msearch_template_named_root_search`
- `regexp_query_search`
- `terms_set_query_search`
- `wildcard_query_search`
- `nested_query_search`
- `rank_eval_precision_search`
- `pit_open_search`
- `pit_list_search`
- `pit_clear_all_search`
- `pit_clear_all_body_search`
- `pit_search_after_close_missing_context`
- `pit_search`
- `pit_search_extends_keep_alive`
- `pit_search_with_routing_filter`
- `pit_snapshot_after_update_delete_search`
- `pit_search_with_default_ignore_throttled`
- `pit_search_with_order_sensitive_default_wildcards`
- `pit_search_with_default_ccs_minimize_roundtrips`
- `scroll_initial_search`
- `scroll_follow_up_search`
- `collapse_search`
- `profile_search`
- `rescore_search`
- `search_coordinator_knobs_search`
- `allow_partial_search_results_true_search`
- `completion_suggest_search`
- `highlight_search`
- `terms_aggregation`
- `composite_aggregation`
- `geo_bounds_aggregation`
- `sum_bucket_pipeline_aggregation`
- `scripted_metric_aggregation`
- `partial_shard_failure_geo_search`
- `allow_partial_search_results_execution_summary`
- `expand_wildcards_closed_fail_closed`

Required security cases through `security-authz-compat-report.json`:

- `security_reader_root_search_success`
- `security_missing_target_search_401`
- `security_writer_root_search_403`

Required fail-closed deny ledger:

- `runtime_mappings_request_body_fail_closed`

Promotion is blocked if supported search evidence is present without an
explicit unsupported-option deny ledger.

### <a id="area-knn-vector-indexing-and-query-search"></a>k-NN vector indexing and query search

Promotion is allowed only when the claimed vector subset includes lucene score
spaces, byte/binary behavior, hybrid score merge, nested/filter semantics,
exact ranking evidence, and an explicit reject ledger for unsupported vector
capabilities.

Required route evidence:

- `vector-search-compat-report.json`

Required semantic cases:

- `knn_search`
- `knn_cosinesimil_search`
- `knn_innerproduct_search`
- `knn_query_happy_path`
- `knn_query_filter_happy_path`
- `knn_query_ignore_unmapped_happy_path`
- `knn_query_radial_max_distance_happy_path`
- `knn_query_method_parameters_happy_path`
- `hybrid_query_happy_path`
- `hybrid_should_query_happy_path`
- `hybrid_minimum_should_match_happy_path`

Required vector evidence classes:

- `lucene-score-space`
- `byte-vector-subset`
- `binary-vector-subset`
- `nested-filtered-knn`
- `exact-ranking`
- `hybrid-score-merge`

Required reject ledger categories:

- `engine`
- `mode`
- `space`
- `data_type`

Promotion is blocked if vector route parity exists without explicit reject
coverage for unsupported engine/mode/space/data_type combinations.

### <a id="area-knn-plugin-rest-and-model-apis"></a>k-NN plugin REST and model APIs

Standalone promotion is allowed only when settings, warmup, clear-cache,
model-lifecycle, and breaker semantics are all present in the same vector
profile gate.

Required route evidence:

- `knn-plugin-compat-report.json`

Required semantic cases:

- `knn_settings_readback`
- `knn_warmup_basic_shape`
- `knn_clear_cache_basic_shape`
- `knn_model_lifecycle_shape`
- `knn_warmup_budget_failure`
- `knn_warmup_clear_cache_telemetry_shape`

Required plugin evidence classes:

- `settings-readback`
- `warmup-cache`
- `clear-cache`
- `model-lifecycle`
- `budget-breaker`

Explicitly excluded from the standalone claim:

- `secure-clustered-lifecycle`

Any secure clustered lifecycle statement must be promoted separately through a
secure or distributed claim gate instead of through the standalone plugin gate.

### <a id="area-ml-commons-neural-search-and-model-serving"></a>ML Commons, neural search, and model serving

Standalone promotion is allowed only when task lifecycle, deploy/predict
behavior, connector authz, neural query rewrite, rerank, sparse encoding, and
runtime or deployment isolation evidence are all present in the same gate.

Required route evidence:

- `ml-model-surface-compat-report.json`

Required semantic cases:

- `ml_model_lifecycle_shape`
- `neural_query_search`
- `rerank_pipeline_search`
- `sparse_encoder_search`

Required security cases through `security-authz-compat-report.json`:

- `security_bad_password_ml_register_401`
- `security_writer_ml_connector_create_403`
- `security_admin_ml_connector_create_success`
- `security_writer_ml_predict_403`

Required ML evidence classes:

- `task-lifecycle`
- `connector-authz`
- `deploy-persistence`
- `neural-query-rewrite`
- `rerank-pipeline`
- `sparse-encoder`
- `runtime-isolation`
- `deployment-isolation`

Promotion is blocked if the lifecycle route evidence exists without the
isolation and connector-authz evidence classes.

### <a id="area-snapshot-and-restore"></a>Snapshot and restore

Promotion is allowed only when repository lifecycle, snapshot create/readback,
restore safety, cleanup, searchable or remote repository breadth, and
migration/cutover linkage are all present in the same gate.

Required route evidence:

- `snapshot-lifecycle-compat-report.json`

Required semantic cases:

- `register_snapshot_repository`
- `get_snapshot_repository`
- `verify_snapshot_repository`
- `create_snapshot_happy_path`
- `get_snapshot_happy_path`
- `get_snapshot_status_happy_path`
- `restore_snapshot_happy_path`
- `delete_snapshot_happy_path`
- `cleanup_snapshot_repository_happy_path`
- `restore_snapshot_stale_metadata_failure`
- `restore_snapshot_corrupt_metadata_failure`
- `restore_snapshot_incompatible_metadata_failure`
- `restore_missing_snapshot_failure`
- `cleanup_missing_snapshot_repository_failure`

Required snapshot evidence classes:

- `incremental-snapshot`
- `remote-readonly-repository`
- `searchable-snapshot-mount`
- `restore-option-breadth`
- `repository-type-validation`
- `restore-precondition-safety`
- `cutover-linkage`

Required migration linkage:

- `migration-acceptance/report.json`

Promotion is blocked if snapshot lifecycle evidence exists without restore
safety failure paths or without the migration/cutover linkage report.

### <a id="area-migration-and-replacement-tooling"></a>Migration and replacement tooling

Required migration evidence:

- `migration-cutover-integration-report.json`
- `migration-acceptance/report.json`
- `migration-cutover-go-no-go-report.json`

Required semantic migration cases:

- `template_metadata`
- `index_metadata`
- `alias_metadata`
- `data_stream_metadata`
- `scroll_export_sequence`
- `pit_export_sequence`
- `vector_payload_summary_doc`
- `vector_knn_ranking`

Required migration evidence classes:

- `translation-breadth`
- `scroll-export`
- `pit-export`
- `resumability-checkpoint`
- `approval-gate`
- `rollback-only-rehearsal`
- `rollback-divergence-two-dataset`
- `unsupported-feature-preflight`
- `vector-payload-equivalence`
- `vector-ranking-equivalence`

Required final cutover go/no-go report fields:

- `approval_gate`
- `preflight`
- `rollback`
- `vector_validation`
- `divergence_check`
- `final_decision`

Promotion is blocked if migration acceptance evidence exists without the
unsupported-feature detector feeding the final go/no-go report, or if cutover
and rollback evidence are not aggregated in the same promotion gate.

### <a id="area-steelsearch-multi-node-runtime"></a>Steelsearch multi-node runtime

Required peer-node route evidence:

- `mixed-cluster-failure/<profile>/report.json`
- `rolling-stability/<profile>/report.json`
- `distributed-durability-convergence/<profile>/report.json`

Required peer-node evidence classes:

- `quorum-evidence`
- `publication-ordering`
- `peer-recovery`
- `mixed-write-replication`
- `rolling-stability-transcript`
- `durability-convergence`
- `leader-failover`
- `seed-loss-recovery`

Promote this row only when the same-cluster peer gate ties phase-C mixed-node
failure handling to standalone runtime stability and durability artifacts in a
single claim.

### <a id="area-native-transport-frame-and-opensearch-probe-compatibility"></a>Native transport frame and OpenSearch probe compatibility

Required interop route evidence:

- `phase-b-gap/<profile>/report.json`

Required interop evidence classes:

- `handshake-version-gate`
- `stale-cache-failover`
- `named-writeable-roundtrip`
- `cluster-state-diff-apply`
- `allowlisted-forwarding`
- `mixed-mode-failure-harness`

Required binary dispatch proof:

- allowed actions:
  - `ClusterStateAction.INSTANCE`
  - `SearchAction.INSTANCE`
  - `BulkAction.INSTANCE`
- rejected actions:
  - `MultiSearchAction.INSTANCE`
  - `StreamSearchAction.INSTANCE`
- required ledgers:
  - `transport-action-subset-ledger.json`
  - `transport-negotiation-exception-policy.json`
  - `named-writeable-payload-corpus.json`
  - `cluster-state-diff-apply-transcript.json`

Promote this row only when the external interop gate ties the phase-B harness,
named-writeable corpus, diff-apply transcript, and action allow/reject ledgers
into one binary dispatch claim.

### <a id="area-security-and-access-control"></a>Security and access control

Required secure route evidence:

- `security-authz-compat-report.json`
- `secure-multinode-tls-report.json`
- `security-tenant-role-index-report.json`
- `security-audit-correlation-report.json`
- `security-plugin-api-report.json`
- `security-plugin-write-rotation-report.json`
- `secure-multinode-gap-harness/report.json`

Required secure evidence classes:

- `tls-handshake-matrix`
- `tenant-role-index-isolation`
- `restricted-index-policy`
- `audit-correlation`
- `plugin-api-secret-redaction`
- `plugin-write-cert-rotation`
- `secure-multinode-join`
- `secure-cert-rotation`
- `restricted-index-mutation-deny`

Required secure semantic cases:

- `security_missing_root_info_401`
- `security_reader_root_info_success`
- `security_reader_restricted_index_get_403`
- `security_admin_restricted_index_get_success`
- `security_writer_bulk_partial_authz_denial`

Required final secure claim report:

- `secure-standalone-claim-report.json`

The final secure claim report must fail closed when any required suite is
missing, and it must stay `blocked` until both of the following artifacts are
present:

- `security-redaction-smoke-report.json`
- `secure-durability-restart-report.json`

Promote this row to `Yes` on production readiness only when the final secure
claim report transitions to `ok` with both artifacts present and no required
suite omissions.

### <a id="area-opensearch-comparison-harness"></a>OpenSearch comparison harness

The harness row is a governance and aggregation layer. It does not replace any
feature-specific claim gate for standalone, secure, interop, or peer-node
readiness.

Required harness governance inputs:

- `comparison-harness-required-suites.json`
- `unified-comparison-report-schema.json`
- `common-baseline-aggregation-matrix.json`
- `comparison-harness-failclosed-smoke.json`

Required fail-closed smoke classes:

- `fixture_drift`
- `missing_report_field`
- `stale_generated_artifact`

Promote this row only when the top-level harness gate ties required-suite
manifests, unified schema, baseline aggregation completeness, and fail-closed
smoke evidence into one all-profiles governance claim.

Use the current promotion bookkeeping at
[compatibility-promotion-ledger.md](/home/ubuntu/steelsearch/docs/rust-port/compatibility-promotion-ledger.md)
when deciding which rows are eligible to move from conservative `Partial/No`
matrix status into stronger official replacement claims.

### <a id="area-java-opensearch-data-node-compatibility"></a>Java OpenSearch data-node compatibility

This area is an optional in-progress compatibility track, not a core
replacement-ready row.

Required optional-track evidence:

- `java-data-node-scope-matrix.json`
- `java-mixed-cluster-binary-profiles.json`

Required binary harness profiles:

- `java-primary-rust-replica`
- `rust-primary-java-replica`
- `java-driven-rolling-restart`
- `peer-recovery-interruption`
- `segment-compatibility-verify`

Keep this row outside core replacement readiness even when the optional gate is
green.

### <a id="area-java-plugin-abi-compatibility"></a>Java plugin ABI compatibility

This area is an optional in-progress compatibility track, not a core
replacement-ready row.

Required optional-track evidence:

- `java-plugin-abi-scope-matrix.json`
- `java-plugin-compat-layer-profiles.json`

Required compatibility profiles:

- `plugin-bootstrap-config`
- `plugin-rest-binding`
- `plugin-transport-binding`

Keep this row outside core replacement readiness even when the optional gate is
green.
