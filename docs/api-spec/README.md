# Steelsearch API Spec

This directory records the intended meaning of OpenSearch-facing APIs and the
current Steelsearch behavior for each API family.

It is deliberately split into two layers:

- human-readable API specs in this directory;
- source-derived machine inventories in `docs/rust-port/generated/`.
- generated route inventories, evidence matrix, and OpenAPI artifact in
  `docs/api-spec/generated/`.

## Scope

These specs answer three questions per API family:

1. what the OpenSearch API means semantically;
2. what Steelsearch currently implements;
3. whether the current behavior is sufficient for the current replacement
   phase or still incomplete.

This directory is not a claim of production parity. It is a compatibility and
release-gate ledger for standalone replacement plus clearly separated later
interop and mixed-cluster work.

For later phases, read the boundary this way:

- `Phase B` means external Java OpenSearch interop where Steelsearch acts as a
  coordinator, observer, or explicitly gated forwarder;
- `Phase C` means same-cluster peer-node participation, shard lifecycle, and
  recovery/publication parity. Its canonical evidence owner is
  `tools/run-phase-c-mixed-cluster-harness.sh` plus the `mixed-cluster-*`
  report set and `mixed-cluster-reject-ledger.json`.

## Relationship To Milestones And Tasks

The documents in `docs/api-spec/` and the checklist in `tasks.md` do not use
exactly the same unit of progress:

- `docs/api-spec/` describes OpenSearch-facing contract status by API family or
  transport action surface.
- `tasks.md` tracks implementation work items, validation work, and milestone
  backlog for Steelsearch.
- `docs/rust-port/milestones.md` defines which gaps are Phase A standalone
  replacement work versus later mixed-cluster work.

This means a completed task does not automatically imply that an entire API
family is now `Implemented`. For example:

- a transport probe or decode-only feature may complete a task while the
  corresponding server-side OpenSearch transport action remains `Planned`;
- a REST route may be `Partial` even when several supporting implementation
  tasks are already complete;
- a fail-closed response can be correct for the current phase even when full
  semantic parity is still pending.

When these sources appear to disagree, interpret them in this order:

1. `docs/rust-port/milestones.md` for phase intent and completion gate.
2. `docs/api-spec/` for user-visible compatibility status.
3. `tasks.md` for the concrete backlog still required to move a status forward.

## Generated Artifacts

Generated artifacts that complement the hand-written specs:

- [Generated REST Route Reference](./generated/rest-routes.md)
- [Generated Transport Action Reference](./generated/transport-actions.md)
- [Generated Route Evidence Matrix](./generated/route-evidence-matrix.md)
- `docs/api-spec/generated/openapi.json`

Canonical drift gate for these generated artifacts:

- `tools/check-generated-api-spec.sh`

That drift gate is also wired into the major harness entrypoints so generated
OpenAPI drift blocks profile-backed release evidence rather than remaining a
documentation-only concern.

`Phase A` and `Phase A-1` should be read differently:

- `Phase A` proves runtime-backed standalone replacement for an initial declared
  scope plus explicit fail-closed boundaries;
- `Phase A-1` closes those already-live standalone surfaces into required
  profile-backed parity, so the remaining work should read as either:
  - an implemented standalone contract that is owned by a canonical profile, or
  - explicit `Phase B` / `Phase C` work outside standalone replacement.

When a document still says `Partial`, read that as:

- the route family is live and gated by the named profile;
- the documented contract is the required standalone contract for `Phase A-1`;
- any broader non-claimed semantics belong to later interop, same-cluster, or
  Steelsearch-only extension work rather than to an unfinished "development
  subset" placeholder.

## Phase A Acceptance Harness Rule

The Phase A acceptance harness is the evidence layer that ties milestone intent
to API-family status.

- it must stop before comparison if
  `cargo check -p os-node --features development-runtime --bin steelsearch`
  fails, because a
  helper-only or local-harness-only implementation is not enough to claim
  runtime readiness;
- it must compare Steelsearch and OpenSearch on the same declared input for the
  supported subset;
- it must check both success-path compatibility and representative fail-closed
  error behavior;
- it must not be treated as complete merely because one route family has local
  fixtures or one-off comparison scripts.

Harness work is only meaningful when its canonicalization, fixture setup, and
execution entrypoints are defined well enough that different API families can
reuse the same comparison discipline.

### Side-By-Side REST Harness Shape

The minimum reusable harness case should have these parts:

1. a declared request input shared by Steelsearch and OpenSearch;
2. a fixture/setup phase that prepares both sides for the same comparison
   scenario;
3. two executions against the same route family;
4. canonicalization of success or failure output according to the comparison
   rules for that family;
5. a final comparison result that says `match`, `expected fail-closed`, or
   `mismatch`.

Use `tools/run-phase-a-acceptance-harness.sh` as the canonical local or CI
entrypoint for this reusable comparison shape.

Before the side-by-side comparison runs, that entrypoint should enforce a
runtime-backed preflight gate:

1. run `cargo check -p os-node --features development-runtime --bin steelsearch`;
2. record the result as reviewer-facing preflight evidence;
3. stop immediately if the compile gate fails;
4. only then continue to real Steelsearch/OpenSearch route comparison.

This separates three evidence classes that must not be conflated:

- helper-only evidence:
  source-owned builders, contracts, or fail-closed helpers that are not yet
  proven through the runtime path;
- local-harness evidence:
  synthetic dispatch or extracted handler tests that do not traverse the real
  `SteelNode` HTTP/runtime route;
- runtime-backed evidence:
  compile-passing `os-node` plus real acceptance-harness route execution.

Expected artifact layout for that entrypoint:

- `target/phase-a-acceptance-harness/local/compare`
- `target/phase-a-acceptance-harness/local/rehearsal`
- `target/phase-a-acceptance-harness/ci/compare`
- `target/phase-a-acceptance-harness/ci/rehearsal`

The `compare/` tree holds reviewer-facing reports, while `rehearsal/` holds the
repeatable fixture and daemon lifecycle work area behind those reports.

Canonical artifact names under `compare/`:

- always-on report:
  `runtime-precheck-report.json`
  (`cargo check -p os-node --features development-runtime --bin steelsearch`
  preflight gate, compile result, and runtime-backed evidence eligibility)
  `search-compat-report.json`
  `cluster-health-compat-report.json`
  `allocation-explain-compat-report.json`
  (`/_cluster/allocation/explain` primary happy-path and replica unassigned-path)
  `cluster-settings-compat-report.json`
  (`persistent`/`transient` runnable readback subset, bounded write subset,
  live-route response semantics, and fail-closed read/write params)
  `cluster-state-compat-report.json`
  `root-cluster-node-compat-report.json`
  `tasks-compat-report.json`
  (`/_cluster/pending_tasks` shape, `/_tasks` shape, and unknown cancel failure
  shape)
  `stats-compat-report.json`
  (`/_nodes/stats` shape, `/_cluster/stats` numeric subset, and `/_stats`
  numeric subset)
  `index-lifecycle-compat-report.json`
  (`PUT`/`GET`/`HEAD`/`DELETE` bounded index lifecycle subset and missing-delete
  error shape)
  `mapping-compat-report.json`
  (`GET`/`PUT` mapping bounded subset and incompatible update failure shape)
  `settings-compat-report.json`
  (`GET`/`PUT` index settings bounded mutable subset and validation failure shape)
  `single-doc-crud-compat-report.json`
  (single-document `PUT`/`GET`/`POST`/`DELETE` happy-path subset plus
  version-conflict and missing-document error shapes)
  `refresh-compat-report.json`
  (`POST /{index}/_refresh` bounded `_shards` shape and post-refresh/write
  visibility subset)
  `bulk-compat-report.json`
  (`/_bulk` partial failure item shape and `/{index}/_bulk` default-target
  item metadata subset)
  `routing-compat-report.json`
  (custom routing write/get/delete/search visibility subset)
  `alias-read-compat-report.json`
  (`GET /_alias`, `GET /{index}/_alias/{name}`, wildcard alias readback, and
  bounded alias write-index/filter/routing mutation subset)
  `template-compat-report.json`
  (component/composable/legacy template bounded CRUD and readback subset)
  `snapshot-lifecycle-compat-report.json`
  (repository register/get/verify plus snapshot create/get/status/restore/delete/
  cleanup bounded subset and missing-snapshot failure shape)
  `data-stream-rollover-compat-report.json`
  (data-stream fail-closed vs supported OpenSearch reads, and rollover
  fail-closed vs missing-target OpenSearch behavior)
- opt-in reports:
  `migration-cutover-integration-report.json` when OpenSearch export ->
  Steelsearch import/search cutover integration is enabled
  `vector-search-compat-report.json` when bounded `knn_vector`/`knn`/hybrid
  compatibility comparison is enabled
  `multi-node-transport-admin-report.json` when Steelsearch-only two-node
  transport/admin topology validation is enabled
  `http-load-comparison.json` when HTTP load comparison is enabled
  `alias-template-persistence-report.json` when alias/template live comparison
  is enabled

Under `rehearsal/`, keep daemon/fixture work files stable enough for reuse, but
do not treat ad hoc internal filenames there as reviewer-facing canonical
report names.

### Local OpenSearch / Fixture Environment

Every reusable harness scenario should document a local comparison environment
with:

- one Steelsearch endpoint and one OpenSearch endpoint;
- a repeatable seed/setup step for indices, mappings, documents, and cluster
  preconditions required by the scenario;
- a reset boundary that tells the reviewer whether the next case can reuse the
  same environment or must recreate it from scratch.

When documenting that setup, keep two layers separate:

- shared reusable seed:
  common baseline state that multiple cases in the same family can rely on;
- per-case reset boundary:
  the point where a case must recreate, clear, or reseed state before the next
  comparison so that cross-case mutations do not leak forward.

Example split:

- shared reusable seed:
  one precreated index family, shared mappings, and a stable baseline document
  set reused by multiple read/search cases;
- per-case mutation reset boundary:
  after a bulk-write, delete, or update scenario, recreate or reseed the
  mutated target before the next comparison case runs.

For Phase A, treat that read/search seed plus write-path reset split as the
canonical example pair unless an API-family spec documents a narrower fixture
discipline.

Example harness readings:

- success-path match:
  reuse one read/search seed, run the same `GET` or `_search` input on both
  sides, canonicalize field ordering and documented volatile ids, then expect
  `match`;
- expected fail-closed:
  reuse the same declared request shape for an unsupported option family, keep
  the failure noun phrase anchor, then expect `expected fail-closed` rather
  than a synthetic success shell;
- fixture reuse boundary:
  reuse the same seed across read-only cases, but recreate or reseed after a
  write-path case before the next comparison begins.

Keep that order as the canonical teaching sequence:

1. success-path match first;
2. expected fail-closed second;
3. fixture-reset boundary last.

### Success-Response Canonicalization

For success-path comparison, canonicalize only non-semantic variance:

- normalize JSON object field ordering;
- mask or drop documented volatile fields such as timestamps, generated ids, or
  runtime-dependent node/task identifiers when the API-family spec already
  marks them as non-deterministic;
- preserve user-visible success semantics, including status-bearing booleans,
  counters, route-level field presence, and documented result classes.

Canonical volatile-field categories for success responses:

- wall-clock timestamps;
- generated ids or ephemeral request correlation ids;
- runtime-dependent node ids, task ids, transport addresses, or similar
  topology-local identifiers;
- other fields explicitly documented in an API-family spec as
  non-deterministic comparison noise.

Allow an exception outside those categories only when both of the following are
true:

- the field is proven to vary non-semantically across repeated runs of the same
  declared scenario;
- the API-family spec or harness note explains why masking that field does not
  hide a user-visible contract difference.

Every such exception should carry a reviewer-visible note. Do not allow
success-response masking to expand silently outside the canonical volatile
categories.

### Failure-Response Canonicalization

For failure-path comparison, preserve the contract-bearing parts first:

- HTTP status;
- `error.type`;
- `error.reason` after only the minimal normalization needed for documented
  volatile fragments;
- resource metadata that the API family treats as user-visible failure context
  (for example target index, task id, or route-scoped selector details).

Do not canonicalize failures so aggressively that different fail-closed
boundaries collapse into the same result.

For `error.reason`, allow only narrow normalization such as:

- quoting or whitespace differences that do not change the boundary meaning;
- documented volatile ids or timestamps embedded in the reason text.

Do not normalize away the noun phrase that identifies the failing option,
selector, route family, or lifecycle boundary.

Treat that boundary-identifying noun phrase as the canonical comparison anchor
for failure responses. If the anchor changes, the harness should prefer
`mismatch` over broader masking even when nearby wording is otherwise similar.

Treat `match`, `expected fail-closed`, and `mismatch` as the canonical final
result vocabulary for the Phase A acceptance harness. Do not introduce
parallel labels such as `pass`, `known gap`, or `soft fail` unless the harness
contract itself is revised.

Do not shorten `expected fail-closed` further. `expected` tells the reviewer
that the negative result is intentional for the active contract, and
`fail-closed` tells them the surface rejected in the documented OpenSearch-like
way rather than merely failing.

## Documentation Synchronization Rule

When synchronizing `docs/api-spec/` with `tasks.md`, keep the following
boundaries explicit:

- close a task only after the corresponding contract, milestone, or fail-closed
  boundary is actually reflected in the relevant spec page;
- do not upgrade an API-family status only because supporting subtasks are
  complete if the user-visible route or transport surface is still narrower;
- prefer a short explicit note about provisional, transport-only, or dev-only
  behavior over leaving status interpretation implicit;
- when source-derived inventory and prose docs diverge, first align the prose
  to the inventory-backed route/action status, then add a note if narrower
  internal capability still matters for planning.

Example:

- if generated REST inventory still marks `GET /_mapping` as `Planned`, keep the
  API-family route status conservative even when some mapping persistence exists
  internally;
- if generated REST inventory marks `GET /{index}/_doc/{id}` as `Stubbed`, do
  not leave the prose doc at `Partial` just because a development-oriented
  fetch shell exists.

## Compatibility Posture Labels

When updating API-family docs, keep the implementation posture explicit instead
of implying more parity than Steelsearch currently has. In particular, separate
the following ideas:

- `transport-only`: compatibility work that exists only at the transport frame,
  request builder, response decoder, probe, or interop scaffolding layer.
- `REST`: compatibility work that is exposed through OpenSearch-shaped HTTP
  routes and response bodies.
- `dev-only`: behavior that is intentionally useful for development rehearsal or
  Steelsearch-native operation, but is not yet a production-grade OpenSearch
  semantic contract.

Recommended wording rules:

- If Steelsearch can decode or forward a Java OpenSearch transport payload but
  does not implement the corresponding server-side action, describe that surface
  as transport-only or interop scaffolding, not as implemented parity.
- If a REST route exists but narrows semantics relative to OpenSearch, describe
  it as `Partial` and call out the missing behavior explicitly.
- If the current behavior is intentionally narrower but still correct for the
  active milestone, say so directly rather than leaving the reader to infer
  whether the gap is accidental.
- If a route or action is intentionally unsupported, prefer documenting the
  fail-closed boundary instead of implying silent omission.

## Transport Inventory Tracking Tags

The generated transport inventory in
`docs/api-spec/generated/transport-actions.md` needs a separate tracking axis
from the high-level compatibility status in the API-family documents.

### Required Tags

- `probe-only`: Steelsearch can connect to Java OpenSearch, issue the request,
  and/or decode the response, but does not claim to serve the transport action
  on a Steelsearch node.
- `server-side`: Steelsearch serves the transport action on its own node for
  the declared supported subset, with OpenSearch-shaped request validation and
  success/failure semantics.
- `mixed-cluster`: the action has evidence that it behaves correctly or fails
  safely when Steelsearch and Java OpenSearch nodes coexist in the same
  transport topology.

### Tagging Rules

- Every generated transport action entry should carry exactly one
  highest-achieved tag.
- Tag progression is monotonic:
  - `probe-only` -> `server-side` -> `mixed-cluster`
- Lower-level evidence must not be used to claim a higher-level tag.
- `REST` support must not be upgraded into a transport tag unless the
  underlying transport contract is also implemented or intentionally declared
  unnecessary for that phase.

### Core Transport Backlog Reading Rule

When reading the core transport parity backlog, use the generated transport
inventory as the canonical action list and the tags above as the canonical
progress axis.

- treat action-family prioritization, fixture planning, and normalization rules
  as support machinery for moving an action from `probe-only` to
  `server-side` or `mixed-cluster`;
- do not treat completion of shared test or fixture work as equivalent to
  action-level server-side parity;
- when a transport action family has acceptance criteria but no achieved tag
  upgrade yet, keep its user-visible status conservative until the generated
  inventory reflects the higher tag.

Example:

- `ClusterStateAction` may have fixture topology, request builders, and
  comparison normalization ready while still remaining below `server-side`
  until Steelsearch actually serves the declared subset on its own node;
- task action families may already have `probe-only` or comparison scaffolding
  without yet claiming `mixed-cluster`, if cancellation and lifecycle behavior
  has not been validated in a mixed topology.

### Phase A Standalone Transport/Admin Action Buckets

For the standalone replacement gate, read the remaining internal
transport/admin surface in three buckets:

- `Tier 1: cluster liveness and readback`
  - cluster health
  - cluster state
  - cluster settings
  - task listing/cancel
  - node/cluster/index stats
- `Tier 2: migration and recovery operations`
  - repository registration/verify
  - snapshot create/status/restore/delete/cleanup
  - allocation explain
  - recovery-adjacent admin readbacks needed by rehearsal
- `Tier 3: later or optional plugin/admin depth`
  - k-NN plugin transport actions
  - ML Commons transport actions
  - decommission/tiering/extension/admin plugin surfaces

Reading rule:

- Tier 1 is the minimum standalone operating envelope.
- Tier 2 materially strengthens migration/cutover credibility for Phase A.
- Tier 3 can stay `Planned` without blocking the standalone replacement gate,
  as long as REST/API docs keep the boundary explicit.

Current Tier 1 server-side transport-handler audit:

- `ClusterHealthAction`
- `ClusterStateAction`
- `ClusterUpdateSettingsAction`
- `ListTasksAction`
- `CancelTasksAction`
- `NodesStatsAction`
- `ClusterStatsAction`
- `IndicesStatsAction`

all still read as `planned` in the generated transport inventory.

That means current REST bounded surfaces for health/state/settings/tasks/stats
must not be read as proof of server-side transport parity yet.

Current Steelsearch-only multi-node integration evidence:

- a dedicated multi-node transport/admin runner now checks the bounded REST
  readback surfaces for health/state/settings/tasks/stats across two
  Steelsearch nodes;
- the Phase A acceptance entrypoint now exposes that runner as a first-class
  `--scope transport-admin` preset and self-starts a two-node Steelsearch
  cluster when node URLs are not pre-provided;
- this is topology-level standalone evidence, not yet OpenSearch transport-tag
  evidence.

### REST And Internal State-Model Consistency Rule

For Phase A standalone replacement, validate REST path progress against the
state model it reads or mutates, not against route presence alone.

Current reading rule:

- if a REST path already uses a source-owned bounded helper for request
  filtering, response shaping, or fail-closed validation, treat that as
  evidence of state-model consolidation;
- if the corresponding transport action is still `planned`, do not upgrade the
  transport/admin status, but do note that REST and service-layer semantics are
  at least being expressed through the same bounded state contract;
- if a REST path and its helper disagree about field presence, error class, or
  bounded subset, prefer the helper/state-model contract and treat the route as
  not yet stable.

## Phase A Supported / Unsupported / Fail-Closed Matrix

| API family | Supported subset | Explicit fail-closed / planned boundary |
| --- | --- | --- |
| Root / cluster / node | root route, cluster health, bounded cluster state, bounded cluster settings, bounded task/stats/allocation explain reads | server-side transport actions still `planned`; unsupported settings/readback params stay fail-closed |
| Index / metadata | bounded index create/get/head/delete, mapping/settings read/update, alias read/mutation, template CRUD/readback | data streams and rollover stay explicit fail-closed; broader metadata/template simulation remains planned |
| Search | bounded lexical subset, bounded aggregation subset, bounded sort/pagination, bounded vector/hybrid subset | highlight/suggest/scroll/PIT/profile/explain/rescore/collapse/stored/docvalue/runtime fields stay fail-closed unless documented otherwise |
| Document / bulk | bounded single-doc CRUD/update, refresh/routing/CAS subset, bounded bulk item semantics | deeper durability/replica/runtime guarantees still require multi-node evidence; unsupported write params stay fail-closed |
| Snapshot / migration | bounded repository registration/verify, snapshot create/status/restore/delete/cleanup subset, bounded cutover rehearsal flow | stale/corrupt/incompatible restore metadata stays fail-closed; broader repository-byte parity and rollback/runbook depth remain planned |
| Vector / ML | bounded `knn_vector`, bounded `knn` / hybrid query subset, selected standalone model-serving/vector flows | plugin engine parity, full ML task/runtime parity, and production isolation stay out of Phase A and/or fail-closed |

## Canonical OpenSearch Comparison Evidence Format

When storing OpenSearch comparison results in a reviewer-facing evidence
document, use this field order:

- `spec_family`
- `surface`
- `declared_subset`
- `comparison_mode`
  - `side_by_side`
  - `steelsearch_only_fail_closed`
  - `transcript`
- `artifact_path`
- `result`
  - `match`
  - `expected fail-closed`
  - `mismatch`
- `evidence_source`
- `notes`

Field semantics:

- `spec_family`
  - the owning Phase A family document such as `root-cluster-node`,
    `index-and-metadata`, `search`, `document-and-bulk`,
    `snapshot-migration-interop`, or `vector-and-ml`
- `surface`
  - the concrete route, route family, or transcript scenario
- `declared_subset`
  - the bounded support or fail-closed contract being claimed
- `artifact_path`
  - canonical report or transcript file path
- `notes`
  - concise reviewer-facing caveats only, not raw logs

## Release Gate Runtime-Connected Evidence Rule

Count a Phase A family toward the release gate only when its evidence is backed
by the real `os-node` runtime path.

Current rule:

- include runtime-connected artifacts such as:
  - `runtime-precheck-report.json`
  - `tools/run-phase-a-acceptance-harness.sh --mode local --scope ...` reports
  - Steelsearch-only topology reports that were produced by live daemon routes;
- exclude helper-only or local-harness-only artifacts from the release gate
  tally, and record them only as supporting notes or blocker context;
- when a family exits cleanly only through a degraded-source policy, keep the
  Steelsearch runtime evidence in scope but state the source-target limitation
  explicitly in reviewer notes.

## Environment Profile Rule

Treat source-compat and runtime-backed validation as profile-driven rather than
single-environment only.

Current rule:

- prefer one common baseline profile whenever the same profile can exercise the
  declared subset on both Steelsearch and OpenSearch;
- split into feature-specific profiles only when a surface requires additional
  environment capabilities that are not part of the common baseline;
- apply the same rule to both sides of the comparison:
  - OpenSearch must expose the source feature surface being compared;
  - Steelsearch must expose the corresponding runtime-connected surface being
    claimed;
- if a family requires a special profile, document that profile as a validation
  prerequisite rather than treating the missing capability as an API mismatch.

Examples:

- `vector-ml`
  - requires a k-NN-capable profile on the OpenSearch side
- `snapshot-migration`
  - requires a snapshot-repository-capable profile such as a `path.repo`
    admission profile on the OpenSearch side
- `transport-admin`
  - requires a multi-node profile on the Steelsearch side

The canonical inventory of profiles, prerequisites, entrypoints, and required
reports is maintained in
[validation-profiles.md](/home/ubuntu/steelsearch/docs/rust-port/validation-profiles.md).

Degraded-source skip policy:

- degraded-source skip is only acceptable in the common local baseline when the
  source environment does not expose the feature-specific prerequisite;
- degraded-source skip is not a substitute for the feature-specific profile
  itself;
- once a feature-specific profile exists for a family, source-compat claims for
  that family should be judged against that profile rather than against the
  reduced baseline.

## Replacement-Critical Regression Suite

Treat the following as the minimum Phase A replacement-critical regression suite:

- runtime gate:
  - `runtime-precheck-report.json`
- root/cluster/node:
  - `root-cluster-node-compat-report.json`
  - `cluster-health-compat-report.json`
  - `cluster-state-compat-report.json`
  - `cluster-settings-compat-report.json`
  - `tasks-compat-report.json`
  - `stats-compat-report.json`
- index/metadata:
  - `index-lifecycle-compat-report.json`
  - `mapping-compat-report.json`
  - `settings-compat-report.json`
  - `alias-read-compat-report.json`
  - `template-compat-report.json`
- document/search:
  - `search-compat-report.json`
  - `single-doc-crud-compat-report.json`
  - `refresh-compat-report.json`
  - `bulk-compat-report.json`
  - `routing-compat-report.json`
- snapshot/migration:
  - `snapshot-lifecycle-compat-report.json`
- Steelsearch-only topology validation:
  - `multi-node-transport-admin-report.json`
  - `multi-node-write-path-report.json`

Opt-in but replacement-relevant when the environment supports them:

- `migration-cutover-integration-report.json`
- `vector-search-compat-report.json`

## Phase A Completion Checklist

Mark Phase A complete only when all of the following are true:

- family docs expose a current supported/unsupported/fail-closed matrix for:
  - root/cluster/node
  - index/metadata
  - search
  - document/bulk
  - snapshot/migration
  - vector/ML
- replacement-critical regression suite artifacts exist and are current for the
  declared subset
- those artifacts come from runtime-connected daemon execution; helper-only or
  local-harness-only artifacts are excluded from the release tally and called
  out separately when they still exist
- the runtime compile gate passes via:
  - `cargo check -p os-node --features development-runtime --bin steelsearch`
- `tools/run-phase-a-acceptance-harness.sh --mode local` exits successfully for
  the current Phase A tree
- fail-closed boundaries are documented for every planned or intentionally
  unsupported surface that remains user-visible
- snapshot/restore/migration cutover evidence exists for the bounded Phase A
  flow
- Steelsearch-only multi-node evidence exists for:
  - write-path propagation
  - transport/admin bounded readback topology checks
- no document claims server-side or mixed-cluster transport parity beyond what
  the generated transport inventory tags currently show
- reviewer-facing evidence records use the canonical comparison format and
  result vocabulary

## Search And Write-Path Backlog Reading Rule

Read search/write-path parity in two linked but separate dimensions:

- `_search` support is mainly about declared live-surface subset versus
  explicit fail-closed option families on an already exposed route;
- document and bulk write-path support is mainly about route-surface maturity
  versus narrower engine/internal capability behind those routes.

That means:

- a search feature may be correctly classified as `Explicit fail-closed` even
  though the parent `_search` route is `Partial`;
- a write-path route may stay `Planned` or `Stubbed` even when some underlying
  engine operation already exists internally.

Example:

- `_search` can stay `Partial` while `highlight` or `scroll` is still
  `Explicit fail-closed`, because those option families arrive on a live
  search surface and must be rejected explicitly;
- `_bulk` can stay `Partial` while individual item types still have different
  semantic depth, because route exposure and item-type parity are separate
  questions.

### Evidence Rules

- `probe-only`: live probe, fixture, or decoder evidence against Java
  OpenSearch.
- `server-side`: Steelsearch integration evidence that the action is accepted
  and served by Steelsearch with the declared contract boundary.
- `mixed-cluster`: mixed-topology or side-by-side evidence that forwarding,
  publication, coordination, or response behavior is safe in the presence of
  Java OpenSearch nodes.

### Fail-Closed Rule

- If an action is only partially implemented, the tag must reflect the highest
  contract Steelsearch can defend for the supported subset.
- Unsupported request shapes must remain explicit rejection paths and must not
  be rounded up to a higher tag.

### Rollout Plan For Filling Tags

Populate transport tags in the generated inventory in the following order:

1. `Tier 0` foundations and already-proven probe paths
   - mark decoder/probe-only actions first, because these are the clearest
     evidence-backed entries.
2. `Tier 1` replacement-critical actions
   - add `server-side` only after Steelsearch integration and OpenSearch
     comparison evidence both exist for the declared subset.
3. mixed-cluster-sensitive actions
   - defer `mixed-cluster` tags until there is explicit topology evidence, not
     just standalone behavior.

For each action entry, record:

- highest achieved tag;
- supporting evidence source:
  - fixture;
  - live probe;
  - Steelsearch integration test;
  - OpenSearch side-by-side comparison;
  - mixed-topology comparison;
- declared unsupported or fail-closed request shapes if the action is only
  partially served.

Do not bulk-upgrade an entire action family at once. Tag action entries
individually based on the strongest evidence available for that specific
contract.

### Markdown And TSV Sync Rule

When transport tracking tags are introduced into generated inventory outputs,
the Markdown and TSV views must be updated together.

- The TSV inventory is the source-shaped exhaustive ledger and must carry the
  tag column if the Markdown view shows it.
- The generated Markdown view may reformat or group the same data, but must not
  invent tags that are absent from the TSV source.
- A transport tag schema change is incomplete unless all of the following are
  updated in the same change:
  - TSV column definition;
  - Markdown rendering of that column;
  - prose documentation in `docs/api-spec/README.md` explaining tag meaning.
- If a tag is temporarily unavailable in one generated view, remove or hide it
  in the other generated view rather than allowing conflicting inventories.

### Transport Tag Column Draft

When transport tags are added to generated inventory outputs, use the following
minimum column set:

- `transport_tag`
  - one of: `probe-only`, `server-side`, `mixed-cluster`
- `evidence_source`
  - comma-separated or list-valued source of proof, for example:
    - `fixture`
    - `live-probe`
    - `decoder`
    - `steelsearch-integration`
    - `opensearch-compare`
    - `mixed-topology`
- `fail_closed_note`
  - short note describing the supported subset boundary or explicit rejection
    rule when the action is not fully served.

Optional future columns may exist, but these three are the minimum needed to
make a generated tag meaningful rather than cosmetic.

### Canonical `evidence_source` Values

Use these spellings exactly:

- `fixture`
- `live-probe`
- `decoder`
- `steelsearch-integration`
- `opensearch-compare`
- `mixed-topology`

Do not introduce ad hoc variants such as `probe`, `integration-test`,
`comparison`, or `mixed-cluster-test`. If the meaning differs materially,
define a new canonical value in this document first.

### Multi-Value Representation

- TSV storage form:
  - use comma-separated canonical values in a single `evidence_source` column.
- Markdown rendering form:
  - render the same values as a comma-separated inline list unless a wider
    table or grouped layout makes bullet formatting clearer.

Do not use different semantic content between TSV and Markdown just because the
presentation differs. The rendered Markdown should be a faithful formatting of
the TSV-backed value set.

### `fail_closed_note` Style Rule

- Keep `fail_closed_note` short, ideally a single clause or sentence fragment.
- Prefer describing:
  - supported subset boundary; or
  - explicit rejection rule.
- Avoid narrative prose, rationale, or milestone discussion in this field.
- Markdown and TSV should carry the same wording; Markdown may wrap visually,
  but should not expand the content.

### `fail_closed_note` Template Draft

Prefer short templates such as:

- supported subset boundary:
  - `supports <declared subset> only`
  - `supports <subset>; rejects <unsupported shape>`
- explicit rejection:
  - `rejects <unsupported option>`
  - `rejects <unsupported metric/filter combination>`
  - `rejects unsupported <request family> semantics`

Keep the wording operational and contract-focused. Do not restate rationale or
implementation history in this field.

### Placeholder Replacement Guidance

- `<subset>`
  - use the smallest meaningful contract phrase, for example:
    - `cluster-wide health status`
    - `basic metric-filtered cluster state`
    - `tracked task list/get/cancel subset`
- `<unsupported option>`
  - name the concrete unsupported option or shape, for example:
    - `wait_for_nodes`
    - `unsupported metric/filter combination`
    - `non-cancellable task cancellation`

Prefer concrete request-surface wording over internal implementation jargon.

### Request Surface Naming Rule

In `fail_closed_note`, prefer canonical route names, parameter names, and
request-surface terms as they appear to OpenSearch users.

- prefer:
  - `wait_for_nodes`
  - `metric/filter combination`
  - `task cancellation`
- avoid:
  - internal helper names;
  - Rust type names;
  - implementation-specific shorthand.

### Route Name vs Parameter Name Priority

- Prefer parameter or request-option names when the rejection is caused by a
  specific option, for example:
  - `rejects wait_for_nodes`
  - `rejects unsupported metric/filter combination`
- Prefer route names only when the unsupported boundary is route-scoped rather
  than option-scoped, for example:
  - `supports /_cluster/health subset only`

This keeps `fail_closed_note` focused on the narrowest user-visible contract
boundary.

### Combined Subset And Rejection Wording

When both a route-scoped supported subset and an option-scoped rejection need
to be conveyed, prefer a combined form:

- `supports /_cluster/health subset; rejects wait_for_nodes`
- `supports /_cluster/state metric subset; rejects unsupported metric/filter combination`

Put the supported subset first, then the rejection clause. Keep both clauses
short.

Use `;` as the default separator between the clauses. Do not use `,` for this
split, because it makes the contract boundary easier to misread.

If a third clause is required, append it as another short `;`-separated
fragment. Preferred order:

1. supported subset
2. primary rejection
3. additional boundary note

Example:

- `supports /_cluster/state metric subset; rejects wait_for_nodes; omits unsupported custom sections`

Allow a third clause only when it adds a distinct user-visible boundary that is
not already expressed by the first two clauses. Do not add a third clause for:

- rationale;
- milestone commentary;
- implementation detail;
- repetition of the same rejection in different words.

Typical allowed third-clause boundary types include:

- `omits unsupported custom sections`
- `readonly for unsupported mutation fields`
- `returns partial field set for supported subset`

Treat `omits`, `readonly`, and `returns partial` as the canonical third-clause
verb family unless a clearly different user-visible boundary requires another
verb.

Allow an exception only when the user-visible boundary cannot be expressed
accurately by `omits`, `readonly`, or `returns partial` without distortion.
When an exception is used, keep it short and document the same boundary style
consistently across related entries.

Do not add a separate marker just because a third-clause verb is exceptional.
The exceptional wording itself is sufficient as long as it still follows the
same short contract-focused style.

Do not maintain a separate inventory just for exceptional third-clause verbs at
this stage. If exception usage becomes frequent enough to create drift, promote
it into a tracked inventory later.

Treat exception usage as frequent enough for inventory promotion when it stops
looking exceptional across multiple related entries or starts creating wording
drift that reviewers cannot resolve mechanically from the current rules.

For this check, treat `multiple related entries` primarily as an API-family
scope, not a tiny related-routes cluster. A related-routes cluster may be a
warning sign, but the promotion threshold is crossed when the pattern spreads
across the family-level surface.

Treat related routes as a warning sign when the same exceptional wording
pattern repeats across closely related routes or route variants
strongly enough that reviewers would likely copy the phrase forward by habit.

This warning should also appear in reviewer guidance: if a reviewer sees the
same exceptional wording pattern spreading through a route cluster, they should
flag it before it silently becomes family-wide drift.

Minimal reviewer warning text:

- `route wording drift: normalize exception wording`

Freeze that phrasing for the minimal warning text. It keeps the exception
context visible while remaining short enough for checklist use, so this tradeoff
should not be re-opened without a broader reviewer-guidance rewrite.

When listing multiple options inside a single clause, prefer `/` for tightly
paired option names and `,` for longer mixed phrases. Avoid `and` unless the
result would become hard to parse otherwise.

Mix `/` and `,` only when there is a clear inner/outer grouping, for example a
paired option inside a broader comma-separated list. Do not mix them for a flat
list of peers.

Allow parentheses only when grouping would otherwise be ambiguous even after
applying the `/` and `,` rules. Parentheses are the exception, not the default.

When parentheses are used, keep `/` inside the grouped pair and `,` outside the
group, for example:

- `rejects (wait_for_nodes/wait_for_status), unsupported metric/filter combination`

Do not use nested parentheses. If more than one grouped level is required, the
clause should be rewritten instead of adding another nesting layer.

When a clause would require nested grouping, prefer:

1. splitting one clause into two shorter clauses; or
2. reducing the option list to the smallest user-visible boundary phrase.

Rewrite before nesting.

When choosing between those two rewrites, prefer splitting into shorter clauses
first. Use boundary-phrase reduction when clause splitting would still leave
the reader with an over-long or repetitive construction.

If the note is still too long after those rewrites, drop the third clause
before expanding the sentence further. The first two clauses carry the primary
contract boundary.

If dropping the third clause removes a secondary but still important boundary,
record that boundary in the richer prose spec for the API family rather than
forcing it back into the compact generated note.

Default placement for that moved boundary is the API family document's
behavior/status section or the closest milestone/compatibility note that
already describes the narrowed contract.

Preferred order:

1. behavior/status section when the boundary changes what users will actually
   see in the response or supported subset;
2. milestone/compatibility note when the boundary is mainly about phase-scoped
   support limits rather than immediate response semantics.

Examples:

- user-visible response semantics:
  - omitted response fields
  - readonly behavior for unsupported mutation fields
  - partial field set returned for the supported subset
- phase note:
  - mixed-cluster behavior not part of the active milestone
  - support limit that matters to milestone scope more than immediate payload shape
  - plugin or feature parity reserved for a later replacement phase

Keep these two groups distinct:

- response-semantics examples should describe what changes in the returned or
  supported behavior today;
- phase-note examples should describe milestone scope or deferred capability,
  not immediate payload shape.

Within phase-note wording:

- `not part of the active milestone` means excluded from the active milestone;
- `reserved for a later replacement phase` means planned follow-up work beyond
  the active milestone.

Prefer `later replacement phase` over `future milestone` when the point is
product-stage sequencing rather than milestone bookkeeping.

If both terms must appear, use `milestone` for the current delivery gate and
`replacement phase` for the broader product-stage roadmap beyond that gate.

Example:

- `not part of the active milestone; deferred to a later replacement phase`

Freeze this phrasing for phase-note examples. It preserves the roadmap boundary
without sounding like ownership assignment, and should stay unchanged unless a
broader milestone-language pass finds a clearer cross-family replacement.

## Status Legend

| Status | Meaning |
| --- | --- |
| Implemented | Steelsearch exposes the route and the main semantics are present for the documented subset. |
| Partial | Steelsearch exposes the route or feature family, but behavior is narrower than OpenSearch. |
| Stubbed | Steelsearch exposes an OpenSearch-shaped shell with development-only or placeholder behavior. |
| Planned | The OpenSearch API exists in source inventory, but Steelsearch does not implement it yet. |
| Out of scope | Explicitly excluded from the current standalone Steelsearch milestone. |

## Documents

- [root-cluster-node.md](./root-cluster-node.md): root, cluster, node, task,
  stats, and operational APIs.
- [index-and-metadata.md](./index-and-metadata.md): index lifecycle, aliases,
  mappings, settings, templates, data streams, and rollover.
- [document-and-bulk.md](./document-and-bulk.md): single-document CRUD, refresh,
  bulk, and write-path semantics.
- [search.md](./search.md): search routes, Query DSL, aggregations, and
  response-shaping features.
- [vector-and-ml.md](./vector-and-ml.md): k-NN, vector indexing, and ML Commons
  surfaces.
- [snapshot-migration-interop.md](./snapshot-migration-interop.md): snapshots,
  migration/cutover, transport interop, and mixed-cluster boundaries.

REST-oriented hand-written specs are also grouped under:

- [rest/README.md](./rest/README.md)

## Exhaustive Inventories

For route-by-route and action-by-action source inventory, see:

- [`docs/rust-port/generated/source-rest-routes.tsv`](/home/ubuntu/steelsearch/docs/rust-port/generated/source-rest-routes.tsv)
- [`docs/rust-port/generated/source-transport-actions.tsv`](/home/ubuntu/steelsearch/docs/rust-port/generated/source-transport-actions.tsv)

These TSV files are more exhaustive than the prose docs here, but they do not
explain semantics in as much detail.

Generated Markdown references derived from those TSV files live here:

- [generated/rest-routes.md](./generated/rest-routes.md)
- [generated/transport-actions.md](./generated/transport-actions.md)
