# Phase A-1: Standalone Fullset Closure

## Goal

`Phase A-1` is the closure stage after the initial `Phase A` gate.

`Phase A` proved that Steelsearch can replace OpenSearch for a runtime-backed
standalone scope with explicit fail-closed boundaries. `Phase A-1` closes those
already-live standalone surfaces into profile-backed parity and moves the
remaining depth work cleanly into later phases or extension ledgers.

The target is not Java interop and not mixed-cluster operation. The target is:

- full standalone OpenSearch-compatible behavior for already exposed Phase A
  route families;
- feature-complete source comparison on the right validation profile for each
  family;
- removal of `Partial` / `Explicit fail-closed` as the terminal state for
  standalone-replacement-critical APIs.

## Boundary Against Phase B And Phase C

`Phase A-1` must not absorb work that belongs to later phases.

Keep work in `Phase A-1` only when all of the following are true:

- the surface is already part of standalone Steelsearch replacement;
- the missing behavior is about standalone route, request, response, search,
  write-path, vector, snapshot, or admin parity;
- the work does not require Java OpenSearch node membership, mixed-cluster
  transport forwarding, or same-cluster shard lifecycle semantics.

Move work to `Phase B` when it requires:

- strict source-side interop profiles;
- Java OpenSearch coordinating/read-only mixed-mode behavior;
- transport/action compatibility whose main purpose is Java interop rather than
  standalone replacement.

Move work to `Phase C` when it requires:

- same-cluster peer participation;
- Java-compatible cluster coordination/publication semantics;
- mixed-node shard allocation, replication, relocation, recovery, or retention
  lease behavior.

## Validation Profile Rule

Validation remains profile-driven.

- Prefer one common baseline profile whenever the same profile can exercise the
  surface on both OpenSearch and Steelsearch.
- Split into feature-specific profiles when the feature requires additional
  capability on either side.
- A degraded-source skip in the common baseline is acceptable only as proof
  that the baseline cannot exercise the feature. It is not fullset proof.
- A `Phase A-1` fullset claim for a family requires the feature-specific
  profile when one is needed.

Representative profile splits:

- `common-baseline`
  - ordinary standalone replacement routes that do not require special source
    plugins or repository settings
- `vector-ml`
  - requires a k-NN-capable OpenSearch profile
- `snapshot-migration`
  - requires a snapshot-repository-capable OpenSearch profile
- `transport-admin`
  - requires a multi-node Steelsearch profile
  - is release-gating for standalone operator/admin parity, with
    `multi-node-transport-admin-report.json` as the canonical evidence artifact

The canonical profile inventory, entrypoints, and report ownership table live
in [validation-profiles.md](/home/ubuntu/steelsearch/docs/rust-port/validation-profiles.md).

## Fullset Closure Areas

### 1. Root / Cluster / Node

Close the remaining standalone gaps on already live operational APIs:

- cluster-health wait semantics and index-scoped forms
- cluster-state filter and metric parity
- cluster-settings full read/write semantics and default handling
- tasks and pending-tasks response depth
- stats and cat API response coverage and formatting
- allocation explain request/response parity for standalone routing/allocation

### 2. Index Lifecycle And Metadata

Close the remaining standalone depth around:

- create-index body parity
- get/delete/head selector parity
- mapping merge/update parity
- settings update/readback parity
- alias read/write bulk parity
- component/composable/legacy template full standalone parity
- data streams and rollover implementation instead of fail-closed behavior

### 3. Document And Write Path

Close the remaining write-path semantics for standalone replacement:

- full single-document route parity
- full bulk metadata and item semantics
- refresh policy semantics
- routing semantics
- optimistic concurrency edge cases
- auto-create / write alias semantics
- external versioning and remaining update/delete conflict classes

### 4. Search

Close all remaining standalone search surfaces that belong to
standalone replacement:

- remaining Query DSL families
- response shaping options
- search sessions and traversal
- remaining aggregation families/options
- shard-failure / timeout / partial-success semantics
- cat/search-related text and JSON operator surfaces

### 5. Snapshot And Migration

Move from bounded lifecycle support to standalone fullset closure for the
chosen repository-backed replacement flow:

- repository registration/readback/verification parity
- create/status/restore/delete/cleanup option parity
- restore failure-path parity
- migration/export/import strict-profile validation

### 6. Vector / ML

Close the standalone vector surface on the chosen OpenSearch-compatible profile:

- `knn_vector` mapping option closure
- `knn` query option closure
- hybrid search closure
- `/_plugins/_knn/*` operational closure
- ML/model route closure for the standalone profile actually claimed

### 7. Transport / Admin

Within standalone-only scope:

- close remaining admin readback gaps that are already live on the REST/admin
  surface;
- require the `transport-admin` profile itself to clean-pass and contribute
  `multi-node-transport-admin-report.json` to the release-gating evidence set;
- keep same-cluster transport/publication semantics deferred to later phases.

## Exit Criteria

`Phase A-1` is complete only when:

- the Phase A family docs no longer describe standalone-critical surfaces as
  merely bounded subsets where the route is already live;
- feature-specific profiles exist wherever fullset proof cannot be established
  on the common baseline;
- fullset claims are backed by runtime-connected Steelsearch evidence and
  side-by-side source comparison on the appropriate profile;
- remaining unsupported items are genuinely deferred to `Phase B` or `Phase C`,
  not just left as standalone fail-closed shortcuts.

## Completion Checklist

Treat `Phase A-1` as complete only when all of the following are true:

- `tools/run-phase-a-acceptance-harness.sh --mode local` exits `0` on the
  common-baseline tree.
- feature-specific profile runners all exit `0`:
  - `--scope search-execution`
  - `--scope snapshot-migration`
  - `--scope vector-ml`
  - `--scope transport-admin`
- the canonical strict reports exist and clean-pass for their owning families:
  - `search-compat-report.json`
  - `snapshot-lifecycle-compat-report.json`
  - `migration-cutover-integration-report.json`
  - `vector-search-compat-report.json`
  - `ml-model-surface-compat-report.json`
  - `multi-node-transport-admin-report.json`
- generated API spec artifacts are drift-free:
  - `tools/check-generated-api-spec.sh`
- `docs/api-spec/*` describe already-live standalone-critical families as
  current standalone contracts or explicit later-phase defers, not as
  development subsets.
- `docs/rust-port/*` no longer carry stale `MVP`, `development-only subset`, or
  outdated blocker wording for completed `Phase A-1` work.
- any remaining non-claims are explicitly one of:
  - `Phase B`
  - `Phase C`
  - Steelsearch-only extension
