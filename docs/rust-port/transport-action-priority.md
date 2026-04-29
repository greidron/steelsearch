# Transport Action Priority

This document prioritizes OpenSearch transport actions for Steelsearch using the
inventory in `docs/api-spec/generated/transport-actions.md`.

The generated inventory remains the exhaustive list. This file adds
implementation order for replacement milestones.

## Priority Rules

- `Tier 0`: already-covered transport foundations such as handshake, frame
  compatibility, error decode, compression decode, cluster-state request
  builders, and cluster-state decode/probe support.
- `Tier 1`: read/admin actions required to make a Steelsearch-only cluster a
  credible standalone replacement for common operational and observability
  workflows.
- `Tier 2`: read/admin actions that materially improve replacement coverage but
  are not the first gate for Phase A.
- `Tier 3`: actions that are primarily mixed-cluster, repository/migration
  expansion, or plugin-oriented follow-up work.

## Tracking Boundary: Probe Compatibility vs Server-Side Parity

Steelsearch must not treat these as the same class of progress.

### Probe / Interop Compatibility

This includes:

- frame and stream compatibility;
- handshake success;
- request builders that Java OpenSearch accepts;
- response decoders, cluster-state readers, and publication diff readers;
- read-only probes and compatibility scaffolding.

This proves Steelsearch can talk to OpenSearch over transport in a limited or
observational way. It does **not** prove that Steelsearch implements the
corresponding OpenSearch transport action as a server.

### Server-Side Transport Parity

This includes:

- receiving the OpenSearch transport action on a Steelsearch node;
- validating the request with OpenSearch-compatible semantics;
- executing the action against Steelsearch state;
- returning OpenSearch-compatible success and failure responses;
- supporting the action as part of real cluster or admin behavior rather than
  decode-only scaffolding.

### Tracking Rule

- A probe or decoder milestone may close a transport interop task.
- It must not close a server-side transport parity task unless Steelsearch can
  actually serve that action correctly.
- When a route is satisfied through REST-only behavior, keep that progress
  separate from server-side transport parity unless the transport contract is
  also implemented.

### Tracking Buckets

Every transport-facing feature should be tracked in exactly one primary bucket.

- `probe-only`
  - Steelsearch can connect to OpenSearch, send a request, and/or decode the
    response, but does not claim to serve the action.
- `server-side`
  - Steelsearch serves the action on its own node with OpenSearch-shaped
    request validation, execution semantics, and response/error shape for the
    declared subset.
- `mixed-cluster`
  - the action is safe and meaningful when Steelsearch and Java OpenSearch
    participate in the same transport topology, including forwarding,
    publication, or coordination-sensitive behavior.

### Evidence Rule Per Bucket

- `probe-only`
  - requires fixture, decoder, or live probe evidence against Java OpenSearch.
- `server-side`
  - requires Steelsearch integration coverage proving the action is accepted
    and served correctly on Steelsearch nodes.
- `mixed-cluster`
  - requires comparative or mixed-topology integration coverage showing the
    action remains correct when Java OpenSearch nodes are present.

### Non-Substitution Rule

- `probe-only` evidence does not satisfy `server-side` parity.
- `server-side` parity in a Steelsearch-only cluster does not satisfy
  `mixed-cluster` safety.
- `REST` parity does not satisfy transport parity unless the underlying
  transport contract is intentionally out of scope for that phase and marked as
  such.

## Tier 1: Phase A Replacement-Critical Read/Admin Actions

- `ClusterStateAction.INSTANCE`
  - Why: cluster metadata visibility is foundational for admin, debugging, and
    many higher-level workflows.
- `ClusterHealthAction.INSTANCE`
  - Why: health reporting is a basic replacement requirement for operators and
    orchestration systems.
- `ClusterStatsAction.INSTANCE`
  - Why: required for cluster-level observability parity beyond health.
- `NodesStatsAction.INSTANCE`
  - Why: node-level runtime and resource visibility is a common operational
    dependency.
- `IndicesStatsAction.INSTANCE`
  - Why: index/shard stats are core replacement surfaces for operators.
- `PendingClusterTasksAction.INSTANCE`
  - Why: task backlog visibility is part of cluster operability.
- `ListTasksAction.INSTANCE`
- `GetTaskAction.INSTANCE`
- `CancelTasksAction.INSTANCE`
  - Why: task inspection and cancellation are user-visible admin contracts.

## Tier 1 Action Scope And Fail-Closed Policy

### `ClusterStateAction.INSTANCE`

- Phase A scope:
  - support the standalone Steelsearch cluster-state read path needed by
    `GET /_cluster/state` and internal observability;
  - preserve OpenSearch-shaped request validation and response framing for the
    supported metrics/filter subset;
  - reject unsupported metrics, filtering combinations, or state sections
    explicitly.
- Fail-closed rule:
  - if the request asks for a section Steelsearch cannot produce with
    trustworthy semantics, return an OpenSearch-shaped validation or
    unsupported-operation style error instead of a partial silent omission.

### `ClusterHealthAction.INSTANCE`

- Phase A scope:
  - support cluster-wide health reporting for standalone Steelsearch clusters;
  - support the declared subset of wait/timeout semantics that Steelsearch can
    enforce correctly;
  - expose enough counters and status fields for orchestration and admin use.
- Fail-closed rule:
  - if wait conditions, index-scoped semantics, or allocation-sensitive fields
    are not implemented correctly, reject them explicitly rather than returning
    misleading green/yellow/red output.

### `ListTasksAction.INSTANCE`, `GetTaskAction.INSTANCE`, `CancelTasksAction.INSTANCE`

- Phase A scope:
  - expose only tasks that Steelsearch actually tracks as first-class runtime
    work units;
  - define task identity, parent/child linkage, cancellability, and terminal
    status for the supported task subset;
  - keep response shape OpenSearch-compatible for supported fields.
- Fail-closed rule:
  - if a task family is not yet tracked with reliable lifecycle semantics, it
    must be omitted by documented contract or rejected explicitly, not surfaced
    as fake completed/cancellable work;
  - cancellation must fail explicitly for non-cancellable or unknown task ids.

## Suggested Implementation Order Inside Tier 1

1. `ClusterHealthAction.INSTANCE`
   - Smallest user-visible admin contract and easiest standalone replacement
     win.
2. `ClusterStateAction.INSTANCE`
   - Builds on the existing decode/probe and metadata work, but must become a
     trustworthy server-side contract.
3. task actions
   - Depend on a clearer internal task model and cancellation rules.
4. stats actions
   - Expand once the task and cluster/admin contracts are stable enough to
     measure coherently.

## Tier 1 Implementation And Test Ownership Draft

### 1. `ClusterHealthAction.INSTANCE`

- Primary implementation ownership:
  - `crates/os-cluster-state`
    - health status derivation from cluster metadata and shard/index state;
    - wait-condition evaluation for the declared Phase A subset.
  - `crates/os-transport`
    - transport action registration, request decode, and response/error
      framing.
  - `crates/os-node`
    - REST-to-transport wiring parity where `GET /_cluster/health` and
      transport-backed behavior must agree.
- Required test ownership:
  - `crates/os-node/tests`
    - standalone Steelsearch integration coverage for success, timeout, and
      rejected unsupported wait semantics.
  - OpenSearch comparison harness
    - side-by-side assertions for supported request shapes and comparable
      health fields.

### 2. `ClusterStateAction.INSTANCE`

- Primary implementation ownership:
  - `crates/os-cluster-state`
    - metric filtering, section rendering, and fail-closed handling for
      unsupported state views.
  - `crates/os-transport`
    - action registration and OpenSearch-shaped request/response envelopes.
  - `crates/os-node`
    - consistency between REST `/_cluster/state` output and transport-backed
      state semantics.
- Required test ownership:
  - `crates/os-node/tests`
    - standalone Steelsearch integration coverage for supported metric/filter
      subsets and explicit rejection paths.
  - OpenSearch comparison harness
    - side-by-side assertions for supported metric subsets, absent-field
      policy, and error shape on unsupported combinations.

### 3. `ListTasksAction.INSTANCE`, `GetTaskAction.INSTANCE`, `CancelTasksAction.INSTANCE`

- Primary implementation ownership:
  - `crates/os-node`
    - runtime task registry, task identity, parent/child linkage, and
      cancellation lifecycle.
  - `crates/os-transport`
    - action registration, request validation, and response/error envelopes.
  - `crates/os-cluster-state`
    - no primary ownership, except where cluster-managed operations become
      tracked tasks.
- Required test ownership:
  - `crates/os-node/tests`
    - task listing, point lookup, successful cancellation, rejected
      cancellation, and unknown-task behavior.
  - OpenSearch comparison harness
    - side-by-side assertions for response shape and failure semantics on the
      supported task subset.

### 4. `ClusterStatsAction.INSTANCE`, `NodesStatsAction.INSTANCE`, `IndicesStatsAction.INSTANCE`, `PendingClusterTasksAction.INSTANCE`

- Primary implementation ownership:
  - `crates/os-node`
    - runtime/node/process stats collection and task backlog exposure.
  - `crates/os-cluster-state`
    - cluster/index/shard-derived aggregate counters.
  - `crates/os-transport`
    - transport action registration and response framing.
- Required test ownership:
  - `crates/os-node/tests`
    - standalone Steelsearch integration coverage for declared stat fields and
      fail-closed handling of unsupported sections.
  - OpenSearch comparison harness
    - field-level comparison for supported counters only, with explicit allow
      lists instead of broad snapshot comparison.

### Sequencing Rule

- Do not start stats action parity before `ClusterHealthAction.INSTANCE` and
  `ClusterStateAction.INSTANCE` have stable request validation and fail-closed
  behavior.
- Do not claim task action parity before Steelsearch has a real task registry
  with cancellation semantics; placeholder or synthetic tasks are not
  sufficient.
- Prefer one action family at a time, with:
  - transport handler;
  - Steelsearch integration tests;
  - OpenSearch comparison tests;
  - documentation/spec update;
  completed before moving to the next family.

## OpenSearch Comparison Acceptance Criteria For Tier 1

### `ClusterHealthAction.INSTANCE`

- Required comparison inputs:
  - empty or green standalone cluster;
  - cluster with at least one created index and assigned primary shards;
  - requests with supported `wait_for_status`, `timeout`, and cluster-wide
    scope only;
  - requests using intentionally unsupported wait semantics.
- Acceptance rule:
  - Steelsearch and OpenSearch must agree on the supported request outcome
    class:
    - success vs timeout vs validation-style rejection;
  - for successful requests, compare only the declared supported fields:
    - top-level health status;
    - active shard counters used by the Phase A contract;
    - timed-out indicator when a supported wait condition is used.
- Non-goals for acceptance:
  - do not require byte-identical or full JSON equality;
  - do not accept silent omission of unsupported semantics.

### `ClusterStateAction.INSTANCE`

- Required comparison inputs:
  - default cluster-state request for the declared Phase A metric subset;
  - metric-filtered requests for supported sections only;
  - requests combining supported filters with unsupported metrics or options.
- Acceptance rule:
  - Steelsearch and OpenSearch must agree on:
    - success vs explicit rejection for each request shape;
    - presence of the supported top-level sections;
    - stable field-shape expectations for the supported subset.
  - comparison should be normalized to supported sections and fields rather
    than full cluster-state snapshot equality.
- Non-goals for acceptance:
  - no requirement to match unsupported sections through empty placeholders;
  - no credit for partial responses that hide rejected metrics.

### `ListTasksAction.INSTANCE`, `GetTaskAction.INSTANCE`, `CancelTasksAction.INSTANCE`

- Required comparison inputs:
  - task listing when no supported tasks are active;
  - task listing with at least one known supported Steelsearch task active;
  - point lookup for an existing task;
  - point lookup for an unknown task id;
  - cancellation of a cancellable task;
  - cancellation of an unknown or non-cancellable task.
- Acceptance rule:
  - Steelsearch and OpenSearch must agree on:
    - response class for lookup and cancellation outcomes;
    - task envelope shape for the supported subset;
    - explicit failure semantics for unknown/non-cancellable tasks.
  - comparisons may normalize task ids and timing-dependent fields, but must
    not normalize away lifecycle state or cancellability flags.
- Non-goals for acceptance:
  - no requirement to expose Java-specific internal tasks that Steelsearch does
    not implement;
  - no synthetic "completed" tasks to satisfy shape-only comparison.

### Comparison Harness Rule

- Every OpenSearch comparison test must define:
  - request input;
  - normalization rules for nondeterministic fields;
  - allow-list of compared fields;
  - expected rejection class for unsupported inputs.
- A comparison test is not complete if it only proves both systems returned
  "something". It must prove agreement on the declared contract boundary.

## Tier 1 Fixture Input Draft

### `ClusterHealthAction.INSTANCE`

- Steelsearch integration fixture inputs:
  - single-node empty cluster;
  - single-node cluster with one created index;
  - multi-node Steelsearch cluster with assigned primary shards;
  - request variants:
    - default request;
    - supported `wait_for_status`;
    - supported `timeout`;
    - intentionally unsupported wait option.
- OpenSearch comparison fixture inputs:
  - matching empty cluster topology;
  - matching one-index topology;
  - matching request variants for supported and rejected inputs.

### `ClusterStateAction.INSTANCE`

- Steelsearch integration fixture inputs:
  - empty cluster metadata;
  - cluster with one index and basic mappings/settings;
  - cluster with multiple indices to exercise supported metric filtering;
  - request variants:
    - default metric subset;
    - supported metric-filter combinations;
    - unsupported metric or filter combinations.
- OpenSearch comparison fixture inputs:
  - matching metadata topologies;
  - identical request variants normalized to the declared supported subset.

### `ListTasksAction.INSTANCE`, `GetTaskAction.INSTANCE`, `CancelTasksAction.INSTANCE`

- Steelsearch integration fixture inputs:
  - no active supported tasks;
  - one active cancellable task;
  - one active non-cancellable task if such a task family exists in Phase A;
  - request variants:
    - list all tasks;
    - get existing task id;
    - get unknown task id;
    - cancel existing cancellable task;
    - cancel unknown task id;
    - cancel non-cancellable task id.
- OpenSearch comparison fixture inputs:
  - comparable task-producing request flow for the supported task subset;
  - identical lookup/cancel request variants, with normalization for runtime
    ids and timing-dependent fields only.

### `ClusterStatsAction.INSTANCE`, `NodesStatsAction.INSTANCE`, `IndicesStatsAction.INSTANCE`, `PendingClusterTasksAction.INSTANCE`

- Steelsearch integration fixture inputs:
  - idle single-node cluster;
  - cluster with one index and documents written;
  - multi-node cluster with per-node stat variance where applicable;
  - cluster with at least one pending or active tracked task for
    `PendingClusterTasksAction.INSTANCE`;
  - request variants limited to the declared supported stat groups.
- OpenSearch comparison fixture inputs:
  - matching idle and loaded cluster topologies;
  - equivalent requests with field allow-lists for supported counters only.

### Shared Fixture Rule

- Prefer reusable topology builders over per-test ad hoc setup.
- Keep one canonical fixture per contract boundary:
  - empty cluster;
  - one-index cluster;
  - loaded cluster;
  - active-task cluster;
  - unsupported-request case.
- OpenSearch comparison fixtures should mirror the Steelsearch topology closely
  enough to compare contract behavior, not attempt full internal-state
  identity.

## Nondeterministic Field Normalization Policy

OpenSearch comparison tests may normalize runtime-dependent fields only when
that normalization does not erase contract meaning.

### Allowed Normalization

- generated task ids whose exact numeric or node-local identity is not part of
  the declared contract;
- timestamps and elapsed durations that naturally vary between runs;
- node ids, ephemeral transport addresses, or publish addresses when the test
  only needs to prove node-count or presence semantics;
- ordering of map-like structures when the OpenSearch contract does not require
  stable ordering;
- shard/index iteration order when the compared contract is explicitly order
  insensitive.

### Forbidden Normalization

- health status values such as green/yellow/red;
- timeout outcome and explicit rejection outcome;
- cancellable vs non-cancellable task flags;
- task lifecycle state when that state is part of the supported response
  contract;
- presence or absence of supported top-level cluster-state sections;
- supported stat field names and their compared counter values;
- explicit error type/class boundaries for unsupported requests.

### Review Rule

- If normalizing a field would make two semantically different outcomes appear
  equivalent, that normalization is forbidden.
- Every normalization rule used by a comparison test should be stated inline in
  the test or referenced from a shared normalization helper with the exact
  fields listed.

## Shared Fixture Topology Builder And Request Builder Split

Tier 1 comparison coverage should separate cluster topology setup from
action-specific request generation.

### Topology Builder Responsibility

A shared topology builder should own:

- cluster shape:
  - single-node empty cluster;
  - single-node one-index cluster;
  - multi-node healthy cluster;
  - loaded cluster with documents;
  - active-task cluster;
- reusable index/document seeding;
- waiting for baseline readiness before action-specific assertions begin.

This builder should not encode action semantics such as health wait options,
cluster-state metrics, or task lookup ids.

### Request Builder Responsibility

Per-action request builders should own:

- request variants for `ClusterHealthAction.INSTANCE`;
- metric/filter combinations for `ClusterStateAction.INSTANCE`;
- list/get/cancel variants for task actions;
- stat-group selections for stats actions.

Request builders may depend on topology outputs, such as created index names or
known task ids, but should not own cluster setup.

### Ownership Split

- shared topology builders:
  - primary home in the Steelsearch integration test support layer under
    `crates/os-node/tests`;
- action-specific request builders:
  - colocated with the action family tests that use them;
- OpenSearch side-by-side adapters:
  - wrap the same logical request variants, translating only what is needed to
    issue the request against the Java OpenSearch node under test.

### Rollout Rule

- Build the shared topology layer first for:
  - empty cluster;
  - one-index cluster;
  - active-task cluster.
- Add per-action request builders only after the topology contract is stable.
- Avoid action-specific fixture forks unless the action requires genuinely new
  topology state that cannot be expressed through the shared builder contract.

## Shared Normalization Helper Contract

OpenSearch side-by-side tests should use a shared normalization helper only for
runtime-dependent fields that are explicitly approved for normalization.

### Input Contract

The helper input should include:

- raw Steelsearch response payload;
- raw OpenSearch response payload;
- action family identifier;
- allow-list of fields that may be compared;
- allow-list of fields that may be normalized;
- explicit list of forbidden normalizations for the action family.

### Allowed Transformations

The helper may:

- drop or rewrite approved nondeterministic fields such as task ids,
  timestamps, elapsed durations, and ephemeral addresses;
- canonicalize order-insensitive collections where ordering is not part of the
  documented contract;
- project a larger payload down to the declared compared-field allow-list.

The helper must not:

- rewrite semantic status values;
- convert explicit errors into empty success-like shapes;
- hide presence/absence differences for supported fields;
- normalize different lifecycle or cancellability states into the same output.

### Output Contract

The helper output should be:

- normalized Steelsearch payload;
- normalized OpenSearch payload;
- machine-readable record of which normalization rules were applied.

Comparison assertions should fail if a test attempts to normalize a field that
is not present in the approved allow-list for that action family.

## Shared Topology Builder Handle Contract

The shared topology builder should return a stable handle object instead of
forcing action-family tests to reach into setup internals.

### Required Handle Fields

- cluster readiness:
  - health-ready indicator for the declared baseline state;
  - timeout or readiness failure surfaced explicitly to the caller.
- topology identity:
  - node count;
  - Steelsearch node addresses or endpoints needed by the test harness;
  - OpenSearch node addresses or endpoints when running side-by-side tests.
- seeded resources:
  - created index names;
  - document ids or seed dataset labels when relevant;
  - known task ids for active-task fixtures when task-producing setup is part
    of the topology.
- capability hints:
  - whether the topology is empty, one-index, loaded, or active-task oriented;
  - any declared unsupported features intentionally absent from that topology.

### Contract Rule

- Action-family tests may consume the handle, but should not inspect hidden
  setup internals outside the handle contract.
- If a test needs new setup state repeatedly, promote that state into the
  shared handle instead of creating ad hoc fixture-specific escape hatches.

### Minimum vs Optional Handle Fields

- Minimum fields:
  - readiness outcome;
  - node count;
  - Steelsearch endpoints;
  - topology kind (`empty`, `one-index`, `loaded`, `active-task`);
  - created index names when the topology is index-bearing.
- Optional fields:
  - OpenSearch endpoints for side-by-side runs;
  - seeded document ids or dataset labels;
  - known active task ids;
  - feature-absence hints for intentionally unsupported topology features.

Tests must not assume optional fields are present unless the fixture contract
for that topology explicitly guarantees them.

### Minimum Handle Guarantees By Topology Kind

| Topology kind | Minimum guarantees |
| --- | --- |
| `empty` | readiness outcome, node count, Steelsearch endpoints, topology kind |
| `one-index` | all `empty` guarantees plus created index names |
| `loaded` | all `one-index` guarantees plus seeded document ids or dataset label |
| `active-task` | all `empty` guarantees plus known active task ids when the topology contract promises task-producing setup |

### Topology Kind To Action Family Mapping

| Action family | Positive-path minimum | Rejection-path minimum | Representative rejection scenario |
| --- | --- | --- | --- |
| `ClusterHealthAction.INSTANCE` | `empty`; use `one-index` or `loaded` when shard/index counters are part of the compared contract | `empty` unless the rejection depends on richer shard/index state | `unsupported wait_for_nodes` |
| `ClusterStateAction.INSTANCE` | `one-index`; use `empty` only for explicit empty-state coverage | `empty` for unsupported metric/filter validation that does not depend on populated metadata | `unsupported metric/filter combination` |
| `ListTasksAction.INSTANCE`, `GetTaskAction.INSTANCE`, `CancelTasksAction.INSTANCE` | `active-task` for positive task paths | `empty` for no-task and unknown-task paths; `active-task` when rejection depends on non-cancellable task state | `non-cancellable task cancellation` |
| `ClusterStatsAction.INSTANCE`, `NodesStatsAction.INSTANCE`, `IndicesStatsAction.INSTANCE` | `loaded`; use `one-index` for narrower metadata-only stat subsets | `empty` or `one-index`, depending on whether the rejected stat group requires populated data to exercise validation | `unsupported stat group selection` |
| `PendingClusterTasksAction.INSTANCE` | `active-task` when pending-task semantics are being compared | `empty` unless rejection depends on task-producing state | `unsupported pending-task request shape` |

### Positive-Path vs Rejection-Path Topology Rule

If an action family needs different topology minima for success and rejection
paths, document them separately in the same mapping row or in an adjacent note.

- positive path:
  - the minimum topology needed to prove the supported contract works.
- rejection path:
  - the minimum topology needed to prove unsupported or invalid requests are
    rejected correctly.

Prefer the smallest topology that still proves the intended rejection class.
Do not require a richer topology for rejection-only coverage unless the
rejection semantics themselves depend on that richer state.

### Mapping Table Shape Decision

Use separate `positive-path minimum` and `rejection-path minimum` columns when
the mapping table is next expanded.

Reasoning:

- a single mixed prose column becomes ambiguous once success and rejection paths
  diverge;
- two columns keep fixture selection mechanical for test authors;
- the separation matches the acceptance-criteria split already used for
  supported vs rejected request shapes.

### Rejection Scenario Example Decision

Add a short representative rejection scenario alongside the rejection-path
minimum when the family has more than one plausible rejection shape.

Reasoning:

- the topology minimum alone does not always explain why that topology is
  needed;
- a short scenario label makes it easier to select the right fixture without
  reading the entire acceptance section.

Keep the scenario brief, for example:

- `unsupported wait_for_nodes`
- `unsupported metric/filter combination`
- `non-cancellable task cancellation`

Use the same user-facing vocabulary family as `fail_closed_note`, even though
the mapping-table scenario is only a short label. This avoids documentation
drift between fixture-planning tables and generated compatibility notes.

Default to the short label form such as `unsupported X`, not the full sentence
form `rejects X`, because the mapping table is acting as a compact planning
index rather than a generated compatibility note.

Share the core noun phrase with `fail_closed_note`, but do not require the full
sentence form to match. In practice:

- mapping-table label:
  - `unsupported wait_for_nodes`
- generated note:
  - `rejects wait_for_nodes`

This keeps both surfaces aligned on vocabulary while preserving their different
formatting roles.

Only the leading verb or label form should change. The object phrase should
stay identical unless the API-facing wording itself changes.

When multiple options or request-shape nouns appear in the object phrase,
preserve the same left-to-right order across the mapping-table scenario and the
generated note. Prefer the order users encounter in the request surface, not an
alphabetical reorder.

## Action-Family Normalization Allow/Deny Table

| Action family | Allow normalization | Deny normalization |
| --- | --- | --- |
| `ClusterHealthAction.INSTANCE` | node ids, publish addresses, timing fields | health status, timeout outcome, supported shard counters |
| `ClusterStateAction.INSTANCE` | order-insensitive section ordering, ephemeral node identity fields where not contractually relevant | supported top-level section presence, supported field names, explicit rejection outcome |
| `ListTasksAction.INSTANCE`, `GetTaskAction.INSTANCE`, `CancelTasksAction.INSTANCE` | task ids, timing fields, ephemeral node identity fields | cancellable flag, lifecycle state, success vs unknown-task vs rejected-cancel outcome |
| `ClusterStatsAction.INSTANCE`, `NodesStatsAction.INSTANCE`, `IndicesStatsAction.INSTANCE`, `PendingClusterTasksAction.INSTANCE` | node ids, publish addresses, order-insensitive map ordering | compared stat field names, allow-listed counter values, pending-task presence/absence outcome |

Use this table as the default action-family profile. A concrete test may narrow
normalization further, but it must not broaden normalization beyond this table
without an explicit spec update.

## Normalization Profile Representation Decision

Use a config-shaped representation backed by a small action-family enum, not a
pure enum-only model.

### Decision

- action family should still be identified by an enum-like discriminator;
- the actual normalization contract should live in structured config data for
  that action family.

### Reasoning

- enum-only is too rigid once a family needs:
  - compared-field allow-lists;
  - normalization allow-lists;
  - explicit deny-lists;
  - family-specific notes about fail-closed boundaries.
- pure untyped config is too loose and makes accidental profile drift easier.
- enum + config gives:
  - explicit family identity in test code;
  - structured policy data per family;
  - room for future extension without rewriting the test helper interface.

### Implementation Direction

- one small enum or identifier for the action family;
- one config record resolved from that identifier;
- tests may narrow the resolved config, but must not broaden it without a spec
  update.

### Minimum Config Record Fields

The normalization profile config record should contain at least:

- `compared_fields`
  - allow-list of fields that are asserted after normalization;
- `normalizable_fields`
  - allow-list of runtime-dependent fields that may be rewritten or dropped;
- `forbidden_normalizations`
  - explicit deny-list of fields or semantic categories that must never be
    normalized away;
- `notes`
  - short contract notes, especially where fail-closed or subset semantics are
    important for that action family.

### Semantic Category vs Concrete Field Path

Represent both.

- use semantic categories for rules such as:
  - health status;
  - timeout outcome;
  - cancellability;
  - lifecycle state;
  - supported top-level section presence.
- use concrete field paths for runtime-dependent payload details such as:
  - task ids;
  - timestamps;
  - addresses;
  - specific compared counters.

Reasoning:

- semantic categories prevent accidental normalization of the same concept
  under multiple field names;
- concrete field paths keep the helper precise when only particular payload
  fields are safe to rewrite or project.

The config record should therefore allow both category-level and field-path
entries, with category rules taking precedence when there is a conflict.

### Category Precedence Rule

The shared normalization helper should enforce category precedence, not leave
it to each individual test.

- If a semantic category is marked non-normalizable, no concrete field path
  belonging to that category may be normalized even if it appears in a
  field-path allow-list.
- If a semantic category is marked comparable, the concrete field path may
  still be omitted from comparison only when the action-family profile says the
  field is outside the supported compared subset.
- Tests may narrow field-path usage, but must not override a stricter category
  rule.

### Category-To-Field Mapping Location Decision

Keep the base category-to-field-path mapping in a shared table, with
action-family profiles able to reference or narrow that shared mapping.

Reasoning:

- shared semantic categories such as health status, timeout outcome, and task
  cancellability should not be re-declared independently in every profile;
- a shared table reduces spelling drift and keeps category precedence
  enforceable in one place;
- per-profile narrowing is still needed because not every action family exposes
  every field path in the same way.

Implementation direction:

- one shared category-to-field-path table in the comparison helper layer;
- per-profile config may opt into categories and narrow concrete compared
  fields;
- per-profile config must not redefine the shared category with conflicting
  semantics.

### Initial Shared Category Set

Start with these shared semantic categories:

- `health_status`
- `timeout_outcome`
- `top_level_section_presence`
- `task_cancellability`
- `task_lifecycle_state`
- `node_identity_ephemeral`
- `timing_fields`

These are the first categories because they already recur across the Tier 1
acceptance and normalization rules. New categories should be added only when
they represent a reusable semantic concept across multiple action families.

### Initial Category-To-Field Examples

- `health_status`
  - `status`
- `timeout_outcome`
  - `timed_out`
- `top_level_section_presence`
  - `metadata.cluster_uuid`
  - `routing_table.indices.<index_name>`
  - `nodes.<node_id>.transport_address`
- `task_cancellability`
  - `cancellable`
- `task_lifecycle_state`
  - `completed`
  - `running_time_in_nanos`
- `node_identity_ephemeral`
  - `nodes.<node_id>.transport_address`
- `timing_fields`
  - `timestamp`
  - `took`
  - `running_time_in_nanos`

### Initial Domain-Ambiguity Candidate List

The following paths are good candidates for future domain-specific placeholder
review because a plain `<id>` could hide meaning:

- `nodes.<id>.transport_address`
- `nodes.<id>.attributes.<id>`
- `indices.<id>.shards.<id>.state`
- `tasks.<id>.children[]`

Recommended first-pass replacements:

- `nodes.<id>.transport_address` -> `nodes.<node_id>.transport_address`
- `nodes.<id>.attributes.<id>` -> `nodes.<node_id>.attributes.<attr_key>`
- `indices.<id>.shards.<id>.state` -> `indices.<index_name>.shards.<shard_id>.state`
- `tasks.<id>.children[]` -> `tasks.<task_id>.children[]`

### Response-Shape Path Notation Decision

Use dot-path notation when referring to concrete response-shape paths in shared
category mappings and normalization helper config.

Examples:

- `metadata.cluster_uuid`
- `nodes.<id>.transport_address`
- `task.cancellable`

Use a simple field label only when the field is top-level and unambiguous.

For shared category examples, prefer dot-path precision once a plain field
label would hide response shape or placeholder meaning. Keep top-level
unambiguous labels only where extra path detail adds no practical clarity.

For `top_level_section_presence`, the dot-path examples are concrete witnesses
for section presence, not a narrowing of the category from section-level
semantics to field-level semantics.

This witness-field explanation is mainly needed for
`top_level_section_presence` at the moment. The other current semantic
categories already map more directly to field-level observations and do not yet
need separate witness-language.

If a future semantic category relies on indirect dot-path examples that stand
in for a broader semantic boundary, add the same witness-language explicitly.
Do not assume that readers will infer the distinction automatically.

Minimal witness-language template:

- `the dot-path examples are concrete witnesses for <broader semantic boundary>, not a narrowing of the category to field-level semantics`

Examples for `<broader semantic boundary>`:

- `top-level section presence`
- `shard availability`
- `tracked task lifecycle`

`tracked task lifecycle` is acceptable as a boundary phrase because the task
domain already supplies the missing subject and keeps the phrase compact.

These three examples are intentionally kept at a similar abstraction level:
short semantic phrases, not full response-shape labels.

Keep witness-language boundary examples as noun phrases by default. Do not turn
them into full sentences unless a future category genuinely requires that extra
structure.

Keep these noun phrases short. If a boundary phrase starts accumulating too
many modifiers, prefer splitting the explanation around the template rather than
growing the phrase itself.

Treat modifier build-up as a review smell when extra words stop narrowing the
boundary and start repeating domain context that the surrounding category
already supplies. In practice:
- keep modifiers that distinguish the boundary from a nearby sibling concept;
- drop modifiers that only restate the subject area already obvious from the
  category name;
- if a phrase needs more than one clarifying modifier and still feels cramped,
  keep the shorter noun phrase and move the nuance into the prose around the
  template.

Examples:
- keep `top-level section presence` over plain `section presence` because
  `top-level` distinguishes it from nested field or subsection presence;
- keep `tracked task lifecycle` over plain `task lifecycle` because `tracked`
  marks the supported task subset rather than repeating the task domain itself;
- drop expansions like `cluster task lifecycle` or `search task lifecycle`
  when the surrounding category or action family already makes that subject
  area obvious.

Treat a modifier as subset-signaling when removing it would broaden the phrase
past the actual supported contract boundary. Treat a modifier as merely
descriptive when removing it leaves the supported boundary unchanged and only
changes tone or background detail.

Examples:
- `tracked` in `tracked task lifecycle` is subset-signaling because Steelsearch
  is not claiming arbitrary task lifecycle visibility;
- `top-level` in `top-level section presence` is subset-signaling because the
  category is not about any nested section witness;
- adjectives that only make the phrase sound richer, without narrowing the
  supported contract, should stay out of the noun phrase.

Subset-signaling modifiers should still stay conservative. Keep them only when
the narrower contract boundary is already defined elsewhere in the spec, and
prefer wording that marks scope without implying exhaustive parity.

In practice:
- prefer bounded words like `tracked` or `top-level` when the supported subset
  is explicit;
- avoid expansive words like `full`, `complete`, or `global` unless the spec
  really proves that breadth;
- if a modifier can be read as a parity claim rather than a scope marker,
  replace it with a narrower phrase or move the nuance into prose.

Avoided vs preferred:
- avoid `full task lifecycle`; use `tracked task lifecycle`;
- avoid `complete section presence`; use `top-level section presence`;
- avoid `global shard availability`; use `shard availability`.

Keep these pairs in short verb form rather than symbolic shorthand. Forms like
`X -> Y` or `X / Y` are more compact, but they hide whether the left side is
forbidden or merely less preferred. `avoid ...; use ...` keeps the contract
direction explicit.

Do not split the left-hand side into separate `forbid` versus `discourage`
tracks in this table. The pair examples are style guidance, not protocol error
semantics. If a phrase is truly invalid because it overclaims the contract,
keep using `avoid ...; use ...` here and document the stronger fail-closed
boundary elsewhere in the spec.

Keep that separation explicit. This table is for wording hygiene: how to avoid
overclaiming phrases and what shorter bounded phrasing to use instead.
Fail-closed behavior, explicit rejection semantics, and unsupported request
boundaries belong in the transport compatibility and API contract sections, not
inside the wording pair examples.

For the same reason, keep contract-semantics verbs like `rejects` and
`supports` out of the wording pairs. Pair examples should stay with neutral
style-edit verbs such as `avoid` and `use`, so readers do not confuse them with
actual runtime behavior.

Keep `avoid` as the left-hand verb. We do not switch to weaker verbs like
`skip` or `drop`, because they can sound optional or editorial rather than
normative. `Avoid` is still style guidance, but it more clearly signals that
the left-hand phrase should not be used in compatibility wording.

Keep `use` as the right-hand verb. More conversational verbs like `write` or
`say` are too tied to prose mechanics and too weak about contract-facing
wording choice. `Use` stays short while still pointing at the preferred phrase
that should appear in the spec.

Keep the pair order fixed as `avoid ...; use ...`. The discouraged phrase comes
first so the reader sees the wording hazard before the replacement. Reversing
the order makes the pair feel like a preference hint instead of a corrective
style rule.

Keep the semicolon form rather than arrow shorthand. `X -> Y` looks like a
mechanical rewrite rule, while `avoid ...; use ...` keeps the wording
direction explicit and stays consistent with compatibility wording used for
style guidance, not fail-closed behavior documented in compatibility
contracts.

Here `fail-closed behavior` is intentionally left article-free: it points to
that class of contract behavior without pretending the wording pair is naming a
single canonical contract form.

Freeze that wording here. `single canonical contract form` is the current
balance point between naming weight and abstraction, so further micro-tuning of
that phrase should stop unless a wider wording pass finds a concrete ambiguity.

Current classification:

- keep as top-level label:
  - `status`
  - `timed_out`
  - `timestamp`
  - `took`
- prefer dot-path:
  - `metadata.cluster_uuid`
  - `nodes.<node_id>.transport_address`
  - `task.cancellable`

Do not keep section-level labels such as `metadata` or `nodes` as standalone
shared category examples when a concrete dot-path example is available. Section
names may still appear inside prose, but not as the primary normalized example.

### Wildcard / Id Placeholder Rule

Use angle-bracket placeholders such as `<id>` for identifier-bearing response
paths, not `*`.

Examples:

- `nodes.<id>.transport_address`
- `tasks.<id>.cancellable`

Reasoning:

- `<id>` makes it explicit that the segment is a runtime identifier, not an
  arbitrary wildcard expansion;
- it reads more clearly alongside semantic category documentation.

### Array Index Placeholder Rule

Use `[]` to indicate an array element position in response-shape paths, not
`.<n>`.

Examples:

- `hits.hits[].sort`
- `shards[].state`

Reasoning:

- `[]` signals sequence membership without implying a stable positional index;
- it avoids confusion with numeric fields or literal dotted path segments.

### Map-Key And Array Placeholder Composition

When both a map-key placeholder and an array placeholder appear in the same
path, write them in structural order from left to right.

Examples:

- `nodes.<id>.roles[]`
- `tasks.<id>.children[]`

Do not invert the order or collapse placeholders into a single mixed token.

### Nested Map-Key Placeholder Rule

When multiple map-key placeholders are nested, repeat the `<id>`-style segment
at each structural level instead of inventing a compressed shorthand.

Examples:

- `indices.<id>.shards.<id>.state`
- `nodes.<id>.attributes.<id>`

This keeps the path readable and preserves the actual nesting shape.

When two map-key segments represent materially different user-visible concepts,
prefer concept-specific placeholders such as:

- `nodes.<node_id>.attributes.<attr_key>`
- `indices.<index_name>.shards.<shard_id>`

Keep plain `<id>` only when the key kind is obvious from the immediate field
name or the distinction adds no clarity.

Use domain nouns where they are stable and user-visible, for example
`<index_name>` or `<shard_id>`. Use generic suffix forms such as `_id` or
`_key` only when there is no better domain noun.

When choosing between a bare domain noun and a suffixed domain noun, prefer
the suffixed form when it clarifies what the value represents.

Examples:

- prefer `<index_name>` over `<index>`
- prefer `<shard_id>` over `<shard>`

Use the bare domain noun only when the shorter form is already unambiguous in
the surrounding path.

Do not create a large domain-by-domain suffix matrix yet. Keep the general
priority:

1. stable domain noun with clarifying suffix where needed
2. generic `_id`
3. generic `_key`

Only add domain-specific refinements when concrete ambiguity appears in real
response-shape examples.

## Tier 2: Strong Phase A Follow-Up Read/Admin Actions

- `NodesInfoAction.INSTANCE`
- `NodesUsageAction.INSTANCE`
- `NodesHotThreadsAction.INSTANCE`
- `GetRepositoriesAction.INSTANCE`
- `GetMappingsAction.INSTANCE`
- `GetFieldMappingsAction.INSTANCE`
- `GetAliasesAction.INSTANCE`
- `GetSettingsAction.INSTANCE`
- `ClusterSearchShardsAction.INSTANCE`
- `RecoveryAction.INSTANCE`
- `IndicesSegmentsAction.INSTANCE`
- `IndicesShardStoresAction.INSTANCE`
- `GetDataStreamAction.INSTANCE`
- `DataStreamsStatsAction.INSTANCE`

These actions improve OpenSearch operator expectations and close obvious gaps in
index, metadata, and search-adjacent introspection, but they follow the Tier 1
gate.

## Tier 3: Phase B/C Or Domain-Specific Follow-Up

- repository and snapshot transport actions;
- retention lease actions;
- decommission and tiering actions;
- PIT and scroll transport actions;
- vector/k-NN plugin transport actions;
- write-path mutation actions whose standalone REST contract can be satisfied
  without first achieving Java-compatible server-side transport parity;
- same-cluster coordination and mixed-node lifecycle actions.

These are not unimportant. They are postponed only because they are either:

- broader than the first standalone replacement gate; or
- more naturally tied to mixed-cluster or plugin parity milestones.

## Notes

- A completed probe or decode path does not mean the corresponding transport
  action is implemented server-side.
- For Phase A, the main question is whether the action is required to operate a
  Steelsearch-only cluster as an OpenSearch replacement.
- For Phase B and Phase C, transport parity expands from observability and
  metadata visibility toward forwarding, coordination, recovery, and mixed-node
  safety.
