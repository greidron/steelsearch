# Validation Profiles

## Purpose

This document fixes the canonical validation profiles used by Steelsearch
runtime-backed replacement evidence.

The rule is:

- use one common baseline profile whenever possible;
- split into feature-specific profiles only when the feature requires
  additional source or target capabilities;
- judge every fullset claim against the profile that can actually exercise that
  feature on both OpenSearch and Steelsearch.

## Canonical Profile Inventory

| Profile | Purpose | OpenSearch prerequisite | Steelsearch prerequisite | Canonical entrypoint | Required report / evidence set |
| --- | --- | --- | --- | --- | --- |
| `common-baseline` | Default standalone replacement validation for families that do not require special plugin/repository/topology setup. | Local OpenSearch with ordinary REST/search/index capability. | Single-node Steelsearch daemon runtime. | `tools/run-phase-a-acceptance-harness.sh --mode local` | `runtime-precheck-report.json`, root/cluster/node reports, index/metadata reports, document/write-path reports, `search-compat-report.json` for non-specialized search families. |
| `vector-ml` | Strict vector and ML source comparison for `knn_vector`, `knn` query, hybrid, and `/_plugins/_knn/*` routes. | Docker-backed OpenSearch profile with k-NN plugin surface enabled, including `index.knn`, `knn_vector`, and `knn` query support. | Steelsearch runtime with vector/k-NN routes enabled. | `tools/run-phase-a-acceptance-harness.sh --mode local --scope vector-ml` | `vector-search-compat-report.json` plus actual Steelsearch runtime traffic evidence for vector routes. |
| `snapshot-migration` | Strict snapshot and repository comparison for repository-backed snapshot lifecycle and migration rehearsal. | OpenSearch profile with snapshot repository capability, including usable `path.repo` or equivalent repository admission. | Steelsearch runtime with repository/snapshot routes enabled. | `tools/run-phase-a-acceptance-harness.sh --mode local --scope snapshot-migration` | `snapshot-lifecycle-compat-report.json`, migration/cutover evidence, restore-failure executable strict-profile compare. |
| `transport-admin` | Standalone multi-node operational/admin validation. | None beyond ordinary baseline source target when source comparison is needed; many checks are Steelsearch-only topology checks. | Multi-node Steelsearch cluster with the required node topology. | `tools/run-phase-a-acceptance-harness.sh --mode local --scope transport-admin` | `multi-node-transport-admin-report.json`. |
| `write-path-multi-node` | Multi-node write propagation and post-write visibility validation. | None; this is Steelsearch-only topology evidence. | Multi-node Steelsearch cluster with replication/write-path topology. | `python3 tools/multi_node_write_path_integration.py ...` or the equivalent harness-owned runner | `multi-node-write-path-report.json`. |
| `search-execution` | Multi-shard search execution/accounting validation for `_shards.total|successful|skipped|failed`, `timed_out`, `search_type`, and `allow_partial_search_results`. | OpenSearch profile capable of running multi-primary-shard indices in a single-node dev cluster. | Steelsearch runtime with the same search execution surface and multi-shard accounting implementation. | `tools/run-phase-a-acceptance-harness.sh --mode local --scope search-execution` | `search-compat-report.json` generated from `search-execution-compat.json`, including multi-shard baseline, mixed-mapping shard-failure/partial-success, and true can-match pruning cases. |

## Profile Ownership By Family

### `common-baseline`

Families that should pass on the common baseline:

- root/cluster/node
- index/metadata except data-stream/rollover or other profile-specific closure
- document/write-path single-node parity
- ordinary lexical search and aggregation families that do not require special
  source plugins
- in the full local release gate, search evidence is taken from the strict
  common-baseline fixture while alias-global and cat-global readbacks remain
  owned by their dedicated alias/cat reports to avoid cross-family state drift

### `vector-ml`

Families owned by the vector profile:

- `knn_vector` mapping strict compare
- `knn` / hybrid strict compare
- `/_plugins/_knn/*` strict source comparison
- ML/model-serving surface only if the claimed route family depends on k-NN or
  model/plugin capability absent from the common baseline
- canonical local source target:
  - `tools/run-opensearch-vector-dev.sh`
  - default image `opensearchproject/opensearch:2.19.0`

### `snapshot-migration`

Families owned by the snapshot profile:

- repository registration/readback/verification strict compare
- snapshot create/status/restore/delete/cleanup strict compare
- repository-backed migration rehearsal strict compare
- canonical local repo base:
  - `${OPENSEARCH_ROOT}/build/testclusters/runTask-0/repo`
  - exported into the fixture as `SNAPSHOT_REPOSITORY_BASE_DIR`

### `transport-admin`

Families owned by the transport-admin profile:

- multi-node admin/readback topology checks
- bounded transport/admin runtime evidence that depends on multiple Steelsearch
  nodes being live
- cross-case consistency post-checks for:
  - cluster-name agreement across health/state/stats
  - node-count agreement across health/state/nodes-stats
  - pending-task count vs node task-entry count
  - cluster UUID agreement across top-level and metadata paths
- operator-facing invariant checks for:
  - cluster health/status and node counts
  - cluster-state identity fields
  - cluster settings bounded readback
  - pending-task queue shape
  - task list node/task depth
  - node stats node-count/depth
  - cluster stats node/index counters
  - index stats shard/doc counters

### `search-execution`

Families owned by the search-execution profile:

- multi-shard `_shards.total|successful|skipped|failed` accounting
- `search_type=query_then_fetch|dfs_query_then_fetch` execution-mode parity
- `allow_partial_search_results` parity
- mixed-mapping `geo_distance` induced shard-failure with partial-success hits
- true can-match pruning with `_shards.skipped > 0` via source-capable `match_none` and date-range fixtures
- induced timeout / `timed_out=true` parity is not treated as a Phase A-1 parity blocker anymore: representative source-build probes did not produce a deterministic strict-compare-ready source profile, so follow-up work is deferred to Phase B / feature-profile research

### `write-path-multi-node`

Families owned by the multi-node write profile:

- write propagation
- post-write visibility across nodes
- replica-aware Steelsearch-only topology evidence

## Degraded-Source Skip Rule

Degraded-source skip is baseline-only convenience behavior.

- It is acceptable only when the common baseline cannot exercise a feature that
  belongs to a stricter feature-specific profile.
- It does not prove fullset closure for that feature.
- Once a feature-specific profile is available, the family must be judged by
  that profile instead of by the degraded baseline result.

Examples:

- `vector-ml`
  - if the baseline OpenSearch target lacks the k-NN plugin surface, baseline
    compare may skip, but fullset claims still require the `vector-ml` profile
- `snapshot-migration`
  - if the baseline OpenSearch target does not admit the fixture repository
    path, baseline compare may skip, but fullset claims still require the
    `snapshot-migration` profile

## Relationship To Phase A-1

`Phase A-1` fullset closure requires:

- every family to name its owning profile;
- every owning profile to have a canonical entrypoint and report set;
- no family to use degraded-source skip as a substitute for the profile that is
  actually needed to prove standalone fullset parity.
