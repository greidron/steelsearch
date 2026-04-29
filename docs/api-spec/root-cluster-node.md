# Root, Cluster, And Node APIs

## Milestone Gate

- Primary gate: `Phase A` standalone replacement.
- Later extension: `Phase B` for Java OpenSearch transport/admin interop.
- Final extension: `Phase C` for same-cluster coordination, task, and node-role
  parity where peer-node behavior matters.

## Root/Cluster/Node Parity Reading Rule

Read this API family in three layers:

- identity/readback surfaces such as `GET /`, bounded cluster-state readback,
  and stable node/task summaries;
- development summaries that are intentionally narrower than full OpenSearch
  operational telemetry;
- explicit fail-closed boundaries where Steelsearch must reject unsupported
  state filters, task options, stats groups, or lifecycle surfaces.

Do not promote a root/cluster/node route family from `Partial` to
`Implemented` just because one of those layers is strong in isolation. This
family is only stronger when the identity/readback layer, the summary layer,
and the documented fail-closed boundaries all line up with the active
milestone.

Examples:

- `GET /_cluster/state` is strongest on the bounded identity/readback layer,
  but still depends on explicit reject rules for unsupported metric/filter
  combinations.
- `GET /_nodes/stats` and `GET /_cluster/stats` are summary-heavy surfaces and
  should not be read as full OpenSearch telemetry parity.
- `GET /_tasks` / `POST /_tasks/_cancel` need both stable task summaries and
  explicit fail-closed handling for unsupported filters or non-cancellable
  requests.

## Root APIs

| Route | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| `GET /` | Returns node identity and version metadata used by clients to verify the service they reached. | Returns OpenSearch-shaped core identity fields such as `name`, `cluster_name`, `cluster_uuid`, `version`, and `tagline`. Build metadata is still development-level and not full OpenSearch parity. | Partial |
| `HEAD /` | Liveness-style root probe with empty body and success status. | Returns an empty success response. | Implemented |

Primary source references:

- OpenSearch: `RestMainAction`
- Steelsearch notes: `docs/rust-port/rest-compatibility.md`

## Cluster Health And State

| Route | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| `GET /_cluster/health` | Cluster-wide or index-scoped health summary, including wait semantics and timeout behavior. | Development cluster health summary exists. Top-level counters are present, but index-scoped health, wait parameters, and full allocation semantics are incomplete. | Partial |
| `GET /_cluster/state` | Full cluster-state readback, often filtered by metrics or indices. | Development cluster-state and routing summaries exist, but not full OpenSearch state exposure or filtering behavior. | Partial |
| `GET /_cluster/settings` | Read current persistent and transient cluster settings. | The current live readback surface is bounded to `persistent` and `transient`. Local route activation and compat scaffolding now cover that read-only subset plus fail-closed handling for unsupported readback params, but this still does not imply full OpenSearch route parity or write-path parity. | Partial |
| `PUT /_cluster/settings` | Mutate persistent or transient cluster settings. | A bounded source-owned mutation subset now exists for `persistent` and `transient`, including `acknowledged` response semantics and fail-closed handling for unsupported readback-style params. Local `PUT` route activation and `PUT`→`GET` round-trip evidence now exist for that subset, but side-by-side parity evidence is still narrower than full OpenSearch mutation parity. | Planned |
| `GET /_cluster/pending_tasks` | Returns cluster-manager task backlog. | Development summary exists, not a production-grade task queue implementation. | Partial |
| `GET /_cluster/allocation/explain` | Explains why shards are allocated or blocked. | Steelsearch exposes a development allocation explanation surface. It is useful for local rehearsal, not full OpenSearch allocation-decider parity. | Partial |

### Cluster State Metric And Filtering Contract

For `GET /_cluster/state`, `Phase A` should expose a bounded metric/filter
subset and reject the rest explicitly.

- Supported direction
  - basic top-level state readback needed for development replacement
  - metric-filtered reads only for the subset Steelsearch can map to stable
    cluster-state sections
- Unsupported direction
  - OpenSearch metric combinations that imply sections Steelsearch does not
    expose stably
  - index/filter forms that would suggest parity for unsupported routing or
    metadata detail

Fail-closed rule:

- Unsupported metrics, index filters, or mixed filter combinations must be
  rejected explicitly rather than silently ignored.
- Steelsearch must not return a broader state payload than requested just to
  approximate compatibility.

Metric/filter support sketch:

| Request shape | `Phase A` expectation |
| --- | --- |
| cluster identity subset (for example `cluster_uuid`, `cluster_name`) | Supported |
| top-level state identity subset (for example stable top-level identity fields under the cluster-state envelope) | Supported |
| supported metadata summary subset (for example `metadata.cluster_uuid` and other stable metadata readback fields, not deep metadata parity) | Supported |
| supported node summary subset (for example stable `nodes` identity/readback fields, not full node-detail parity) | Supported |
| supported routing summary subset (for example stable `routing_table` readback fields, not deep routing-table parity) | Supported |
| metric request that asks for unsupported custom or deep routing sections | Explicit reject |
| index/filter request that narrows within the supported metric subset | Supported only if the same stable subset is preserved |
| mixed metric/filter combination that would imply unsupported metadata or routing detail | Explicit reject |

For live-compat fixture coverage, keep the current cluster-health comparison
bounded to:

- cluster-wide top-level counters and status;
- `wait_for_status`;
- timeout behavior demonstrated through `wait_for_nodes`.

Do not add index-scoped health or `wait_for_active_shards` fixture cases until
Steelsearch documents those semantics as stable enough for side-by-side
comparison.

Treat that stability gate as satisfied only when all of the following are
true:

- the same index-scoped health request shape returns the same result class on
  Steelsearch and OpenSearch across repeated seeded runs;
- `timed_out`, shard counters, and health status are stable enough to compare
  without route-specific masking beyond the existing harness rules;
- unsupported sibling parameters still fail closed explicitly rather than being
  ignored or widened into cluster-wide health behavior.

For `metadata`, `nodes`, and `routing_table`, `Phase A` keeps the examples at
the stable summary/readback family level. Exact allow-listed metric names
should be documented separately only after Steelsearch has a stable
OpenSearch-side-by-side mapping for those sections.

Current implementation work for `GET /_cluster/state` also depends on the
route-registration source being workspace-visible. The workspace now exposes a
cluster-state route-registration source file with bounded metric/index parsing,
response-filtering helpers, and a request-shaped live-route invoke helper. The
daemon entrypoint now constructs a runtime route-table slice containing the
canonical `_cluster/state` registry entry, but the concrete `SteelNode`
registry still needs to route real `_cluster/state` traffic through that
slice.

`GET /_cluster/settings` now has a bounded live readback subset even though the
broader route family is still narrower than full OpenSearch parity.
The workspace exposes persisted `cluster_settings` state in gateway metadata
tests, and now also exposes a workspace-visible `_cluster/settings`
route-registration anchor file plus canonical registry entry, response builder,
and invoke hook symbol. The daemon entrypoint now also references that
canonical hook through the registry entry, a source-owned route table, and a
path-to-hook dispatch table, and the source-owned helper now fixes the bounded
`persistent`/`transient` response contract. Unsupported query parameters are
also fixed to a canonical fail-closed bucket in source, the canonical response
builder now consumes that reject helper directly, and a request-shaped invoke
helper exists in the same source-owned file. The canonical hook path now
reuses that request-shaped invoke helper as its happy-path entry, and persisted
cluster-settings state can feed the same helper through a thin adapter that the
live hook now consumes directly, so the bounded live response-contract note and
the persisted-state-backed hook path are the same source-owned story. The
canonical registry entry is also fixed to that persisted-state-backed hook
path. The concrete live REST handler path is still not extracted beyond the
daemon entrypoint, so treat route-source extraction as a prerequisite before
claiming `GET /_cluster/settings` parity work is unblocked. Within the daemon
entrypoint, the source-owned route table, the canonical hook reference, and the
path-to-hook dispatch table now line up on the same `_cluster/settings`
surface, and the dispatch tuple itself is now a source-owned symbol, but that
is still not the same thing as a concrete live REST handler implementation.
The concrete live REST handler body symbol now exists in source and reuses the
persisted-state-backed hook path.
The literal runtime dispatch table now also consumes that same source-owned
dispatch record directly.
The concrete runtime registration body for `/_cluster/settings` is now also a
source-owned symbol.
What still is not proven in workspace-visible source is that real
`/_cluster/settings` traffic reaches that registration body at runtime, even
though the daemon entrypoint now names that registration body as the real-
traffic runtime registration input.
The daemon entrypoint now also names the same table as the real-traffic
dispatch table for that surface.
It also names that same dispatch path as the live readback activation for the
current bounded `persistent`/`transient` semantics.
The live-compat scaffold now lines up with a local live-route activation test,
so the bounded readback subset is live even though the broader route family is
still intentionally narrower than full OpenSearch parity.

The current `GET /_cluster/settings` readback gate is open for the bounded
read-only subset because all of the following now hold:

- local `GET /_cluster/settings` traffic reaches the source-owned runtime
  registration body
- the route returns a live `200` readback with the bounded `persistent` and
  `transient` response shape
- unsupported readback params such as `flat_settings`, `include_defaults`, and
  `local` stay explicit fail-closed
- the live route and the side-by-side compat fixture agree on that same bounded
  surface
What this still does not prove is full route-family parity or broader optional
readback semantics.

`PUT /_cluster/settings` now has a source-owned bounded mutation contract for
`persistent` and `transient`, and that helper returns an `acknowledged`
response plus the updated bounded sections while reusing the same canonical
fail-closed parameter bucket. Local `PUT` activation and `PUT`→`GET`
round-trip evidence now show that bounded mutation subset is live in the local
route surface, but that is still not enough to claim full OpenSearch mutation
parity by itself.

`GET /_cluster/pending_tasks` now has a source-owned bounded response contract
for the top-level `tasks` array plus a stable per-task field subset
(`insert_order`, `priority`, `source`, `executing`, `time_in_queue_millis`,
`time_in_queue`). Local seeded-task route activation now shows queued and
in-flight sources flowing through that bounded array shape, so the current
`Partial` route status has both a concrete response-shape anchor and local
live-route evidence even before OpenSearch side-by-side coverage is extended.

`GET /_tasks`, `GET /_tasks/{task_id}`, and `POST /_tasks/_cancel` now have a
source-owned bounded compatibility contract: list/get success paths are
anchored to the `node`/`id`/`action`/`cancellable` allow-list, cancel success
is anchored to the same bounded envelope, and unknown/non-cancellable error
paths are anchored to canonical OpenSearch-shaped error types. Source-owned
live hook symbols now reuse those same bounded envelopes for list/get/cancel
route shapes, and local route activation tests now exercise list/get/cancel
request shapes against seeded task-registry state. That grounds the remaining
task-parity work in concrete source-owned semantics plus local traffic proof
before side-by-side coverage is added.

`GET /_nodes/stats`, `GET /_cluster/stats`, and `GET /_stats` now have a
source-owned bounded top-level summary contract: node stats keep only `nodes`,
cluster stats keep only `indices` plus `nodes`, and index stats keep only
`_all` plus `indices`. That gives the current Partial stats surfaces a
concrete supported-subset anchor. Source-owned live hooks now reuse those same
bounded summary helpers for route-shaped inputs, and local route activation
tests now exercise all three live endpoints before field-presence and numeric
OpenSearch comparisons are added.

`GET /_cluster/allocation/explain` now has a source-owned bounded development
readback contract for `index`, `shard`, `primary`, `current_state`,
`current_node`, and `node_allocation_decisions`. Within each
`node_allocation_decisions[]` entry, the bounded subset keeps only
`node_name`, `node_decision`, `weight_ranking`, and `deciders`, and each
`deciders[]` entry keeps only `decider`, `decision`, and `explanation`.
Source-owned live hook symbols now reuse that same bounded explanation helper,
and daemon entrypoint references now carry the same route table and runtime
dispatch-table shape for that surface. That gives the current Partial route a
concrete compatibility anchor even before local traffic proof and OpenSearch
side-by-side cases are widened. Local route activation tests now exercise the
real `GET /_cluster/allocation/explain` request shape against a gateway-backed
node and confirm the bounded `current_state` plus
`node_allocation_decisions` surface.

Promote those sections to a separate exact allow-list table only when all of
the following are true:

- the Steelsearch-to-OpenSearch metric mapping is stable across repeated
  side-by-side runs
- unsupported sibling metrics are rejected explicitly rather than omitted
  silently
- the documented allow-list no longer depends on temporary development-only
  naming or provisional summary fields

For this promotion gate, treat repeated side-by-side stability as at least
three consecutive matching comparisons for the same section-level metric
subset. Fewer than three runs are too easy to satisfy by accident; higher
counts belong in a broader validation pass rather than this doc-level gate.

Promotion is section-local, not route-global. If `metadata` meets the gate but
`nodes` or `routing_table` do not, only the `metadata` subset may move to an
exact allow-list table.

When this happens, show the exact allow-list state per subset rather than
marking the whole route as promoted. Use a small per-section status such as
`Promoted` or `Family-level only` so the reader can see which subsets have
exact metric coverage and which still stay at the summary/readback family
level.

Treat `Promoted` and `Family-level only` as the canonical status labels for
this partial-promotion state. Do not introduce parallel labels such as
`Exact`, `Summary-only`, or `Not yet promoted` unless a broader status-label
pass changes the table style across the doc set.

Do not shorten `Family-level only` further in this table. The extra words are
doing useful work: they show that the subset still stays at the
summary/readback family contract rather than an exact allow-listed metric set.

For example, three matching `metadata`-subset comparisons can qualify the
`metadata` allow-list for promotion, but one `metadata` run plus two `nodes`
runs cannot be pooled into the same stability claim.

Until that mapping exists, do not split out a separate exact allow-list table
for those three sections. Keeping them in the support sketch avoids a false
precision claim about exact OpenSearch metric coverage.

## Node, Stats, And Tasks

| Route | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| `GET /_nodes/stats` | Node-level runtime, transport, indexing, search, cache, thread-pool, and resource stats. | Steelsearch exposes local/development node summaries. Full telemetry parity is not implemented. | Partial |
| `GET /_cluster/stats` | Cluster-wide statistics aggregated from node and shard state. | Development summary exists, but not full OpenSearch stat depth or semantics. | Partial |
| `GET /_stats` | Index/shard statistics surface. | Partial stats surface exists for supported storage/runtime features. | Partial |
| `GET /_tasks`, `GET /_tasks/{task_id}`, `POST /_tasks/_cancel` | Task listing, lookup, and cancellation for long-running actions. | Development and compatibility documents track these as remaining transport/admin gaps. They are not full parity today. | Planned |
| `GET /_nodes/hot_threads` | Diagnostic stack and scheduler sampling. | Not implemented as a production-grade equivalent. | Planned |
| `GET /_nodes/usage` | Returns usage counters per action/feature. | Not implemented as a production-grade equivalent. | Planned |

### Development Summary vs OpenSearch Statistics

For `GET /_nodes/stats`, `GET /_cluster/stats`, and `GET /_stats`, Steelsearch
must keep the distinction between a development summary surface and full
OpenSearch statistics semantics explicit.

- `GET /_nodes/stats`
  - Phase A contract: expose only documented local/runtime summary fields that
    Steelsearch actually measures.
  - Do not imply parity for thread pools, caches, transport, indexing, or
    search counters that Steelsearch does not stably compute.
- `GET /_cluster/stats`
  - Phase A contract: expose only aggregated cluster summaries derived from
    Steelsearch's own node/shard model.
  - Do not present OpenSearch-shaped depth as evidence of equivalent
    aggregation semantics unless side-by-side tests prove it.
- `GET /_stats`
  - Phase A contract: expose only supported index/shard summary fields.
  - Do not silently fill unsupported index stats with zeros or placeholder
    objects.

Response-shape rule:

- Development summary routes should keep OpenSearch-like envelope structure
  where that helps compatibility.
- But summary-only fields must not be described or labeled as if they were full
  OpenSearch operational counters.
- Unsupported stat groups or parameters should fail closed rather than degrade
  into misleading partial success.

Labeling rule for summary-only fields:

- Prefer `summary` when the field is intentionally high-level and stable.
- Use `development` only when the field remains explicitly non-contractual or
  temporary.
- Use `partial` for route-level or feature-level support status, not as an
  in-band field label inside the stats payload.

Examples:

- avoid payload field labels like `partial_docs`, `partial_search_stats`
- prefer route or prose status statements such as `Status: Partial`
- allow labels like `development_node_summary` or
  `development_cluster_summary` only when the field is explicitly marked
  non-contractual and temporary

Treat the `development_*_summary` pattern as the canonical naming example for
temporary non-contractual summary fields.

Do not introduce parallel temporary-summary naming patterns unless a broader
stats naming pass revisits the whole route family. Keeping one canonical
pattern is preferable to allowing `dev_*`, `temporary_*`, or mixed variants to
drift into the payload surface.

### Task API Minimum Compatibility Contract

`Phase A` should treat the task APIs as a bounded compatibility surface rather
than a full OpenSearch task-management implementation.

- `GET /_tasks`
  - Scope: list only Steelsearch-tracked tasks that have explicit task-registry
    entries.
  - Required shape: OpenSearch-like top-level task listing envelope with stable
    task identifiers, action names, node identifiers, and cancellable flags for
    tasks Steelsearch truly tracks.
  - Exclusions: no synthetic tasks, no invented lifecycle states, and no
    requirement to expose every internal async operation.
- `GET /_tasks/{task_id}`
  - Scope: lookup only tasks that were previously exposed through the supported
    task registry.
  - Required behavior: return the supported task envelope for known tasks;
    return an OpenSearch-shaped missing-task error for unknown ids.
  - Exclusions: no best-effort reconstruction of expired or never-tracked task
    metadata.
- `POST /_tasks/_cancel`
  - Scope: cancel only tasks that are both tracked and explicitly cancellable.
  - Required behavior: succeed for supported cancellable tasks; fail closed for
    unknown tasks and non-cancellable tasks with an OpenSearch-compatible error
    class.
  - Exclusions: no optimistic cancellation of tasks without real cancellation
    hooks.

Fail-closed rule:

- Unsupported filters, grouping modes, or wait semantics must be rejected
  explicitly rather than ignored.
- Steelsearch must not claim full task parity until list/get/cancel semantics
  are backed by a real shared task registry and side-by-side OpenSearch
  comparison tests.

Task envelope allow-list for `Phase A` comparisons:

- List/get success paths
  - `node`
  - `id`
  - `action`
  - `cancellable`
  - optional evidence fields:
    - `type`
    - `headers`, but only if Steelsearch intentionally exposes the same
      supported header subset
- Lookup/cancel error paths
  - top-level OpenSearch-shaped `error.type`
  - top-level OpenSearch-shaped `error.reason`
  - success/failure result class for known vs unknown vs non-cancellable tasks

Fields outside this allow-list should not be used as parity evidence until
Steelsearch exposes a stable contract for them.

Optional evidence stability conditions:

- `type` may be compared only if Steelsearch uses a stable task-type taxonomy
  rather than an incidental internal label.
- `headers` may be compared only if Steelsearch documents a supported propagated
  header subset and normalizes omissions the same way across repeated runs.

If those stability conditions are not met, the comparison helper should drop the
optional evidence fields from parity assertions rather than treating them as
hard mismatches.

Test-output annotation rule:

- When optional evidence fields are dropped, the comparison output should say
  which fields were excluded and why, so the omission is visible as a conscious
  stability decision rather than silent weakening of the parity claim.

Canonical annotation order:

- field name first
- exclusion reason second

For example: `excluded optional field: headers (unsupported stable header
subset contract)`.

Canonical reason phrases:

- `unsupported stable header subset contract`
- `unstable task-type taxonomy`
- `field not covered by current Phase A parity contract`

Annotation style rule:

- Use the canonical reason phrase by itself for routine exclusions.
- Add free-form explanation only when the canonical phrase alone would hide a
  task-specific compatibility boundary that matters for reviewer interpretation.

Representative cases where free-form explanation is allowed:

- `headers` excluded because only a documented subset is propagated and the
  compared request depends on headers outside that subset.
- `type` excluded because the current test run uses an internal task category
  that is still intentionally collapsed into a broader public action family.

Canonical phrase + free-form explanation template:

- `excluded optional field: <field> (<canonical reason>; <free-form boundary
  note>)`

Use `;` as the fixed separator between the canonical reason phrase and the
free-form boundary note. Do not switch to commas or nested parentheses for this
annotation shape.

Keep the order fixed as canonical reason first, boundary note second. The
stable phrase identifies the comparison policy; the trailing note explains the
task-specific exception.

When the boundary note is omitted, keep the same sentence frame and simply drop
the second clause. For example:

- `excluded optional field: type (unstable task-type taxonomy)`

Singular/plural rule:

- Use `excluded optional field` when one field is omitted.
- Use `excluded optional fields` only when a single annotation intentionally
  covers a grouped omission set.

Representative grouped omission cases:

- `headers` and a related propagated-header-derived field may be grouped when
  both are excluded for the same documented header-subset reason.
- Multiple task-type-adjacent fields may be grouped only if they all depend on
  the same unstable task-type taxonomy boundary.

Same-reason grouping rule:

- Group fields only when the exclusion would use the same canonical reason
  phrase without changing meaning.
- If one field needs a different canonical reason or a different free-form
  boundary note, split it into a separate annotation.

Representative forced-split case:

- `headers` and `type` must not share one grouped omission annotation if both
  use optional evidence exclusion but one needs a header-subset boundary note
  while the other needs a task-type-taxonomy boundary note.
- `headers` and `cancellable` must not share one grouped omission annotation if
  `headers` is excluded for header-subset stability while `cancellable` fails
  because the task is outside the supported cancellation contract.
- `type` and `action` must not share one grouped omission annotation if `type`
  is optional evidence but `action` is a required parity field whose mismatch
  would change the success-path result class.

Optional-vs-required split rule:

- Never group an optional evidence field with a required parity field inside
  one omission annotation.
- Optional evidence omission explains why a non-essential comparison field was
  dropped.
- Required parity field handling must stay visible as a primary comparison
  result, not be hidden inside an omission note.

Comparison output example:

- `excluded optional field: type (unstable task-type taxonomy)`
- `required parity mismatch: action`

Required parity mismatch rule:

- Show the field name first.
- Add a short reason only when it helps distinguish shape mismatch,
  unsupported semantics, or wrong result class.

Canonical required-mismatch reason phrases:

- `shape mismatch`
- `unsupported semantics`
- `wrong result class`

Required-mismatch annotation rule:

- Use the canonical reason phrase alone for routine mismatches.
- Add free-form explanation only when the canonical phrase would hide the
  specific contract boundary that made the mismatch meaningful to a reviewer.

Representative cases where free-form explanation is allowed:

- `action` mismatch where the compared request is routed through a broader
  public action family in OpenSearch but a narrower Steelsearch action name is
  intentionally exposed.
- `cancellable` mismatch where the result depends on whether the task is inside
  the supported cancellation contract rather than on a simple boolean shape
  difference.

Canonical reason + free-form explanation template:

- `required parity mismatch: <field> (<canonical reason>; <free-form boundary
  note>)`

Use `;` as the fixed separator between the canonical reason phrase and the
free-form boundary note here as well. Do not switch to commas or nested
parentheses for required parity mismatch annotations.

Keep the order fixed as canonical reason first, boundary note second. The
stable reason phrase should identify the mismatch class before any
task-specific explanatory note expands it.

When the free-form note is omitted, keep the same sentence frame and simply
drop the second clause. For example:

- `required parity mismatch: action (wrong result class)`

Singular/plural rule:

- Use `required parity mismatch` when one required field fails.
- Use `required parity mismatches` only when a single annotation intentionally
  summarizes a grouped required-field failure set.

Representative grouped required-field failure cases:

- `action` and `cancellable` may be grouped only when both fail for the same
  supported-cancellation-contract boundary and the reviewer does not need two
  separate result-class interpretations.
- Multiple top-level required fields may be grouped only when they all fail as
  one shape mismatch produced by the same unsupported response contract.

Same-reason grouping rule:

- Group required-field failures only when the same canonical mismatch reason
  phrase applies without changing meaning.
- If one field would need a different canonical mismatch reason or a different
  free-form boundary note, split it into a separate mismatch annotation.

Representative forced-split case:

- `action` and `cancellable` must not share one grouped required-field failure
  annotation if both use `unsupported semantics` but `action` needs a public
  action-family boundary note while `cancellable` needs a cancellation-contract
  boundary note.
- `action` and `node` must not share one grouped required-field failure
  annotation if `action` fails because of a public action-family mismatch while
  `node` fails because the comparison cannot map a stable node identity.
- `id` and `cancellable` must not share one grouped required-field failure
  annotation if `id` points to a wrong result-class problem while `cancellable`
  depends on the supported cancellation-contract boundary.

Identity-vs-capability split rule:

- Do not group identity fields such as `node` or `id` with capability fields
  such as `action` or `cancellable` inside one required-parity mismatch
  annotation.
- Identity failures answer “which task/node is this?”.
- Capability failures answer “what does this task support or expose?”.
- Keep those failure classes separate even when they appear in the same
  response, so reviewers can distinguish locator problems from contract-surface
  problems.

Comparison output example:

- `required parity mismatch: node (shape mismatch)`
- `required parity mismatch: action (unsupported semantics; public action-family boundary)`

Same-block example:

```text
required parity mismatch: node (shape mismatch)
required parity mismatch: action (unsupported semantics; public action-family boundary)

Order the block as identity mismatch first, capability mismatch second. The
reviewer should locate the task/node successfully before evaluating what the
task claims to support.

Keep the two lines adjacent with no blank line between them. The point of this
format is to show one compact response block rather than two unrelated reports.

Repeat the full `required parity mismatch:` prefix on each line. Do not shorten
the second line, because each mismatch should remain independently scannable in
logs or copied excerpts.

Keep the same rule even when a same-block example grows beyond two lines. A
longer block still represents multiple independent mismatches, not a single
header plus indented continuations.

Keep same-block examples short. If a block would grow beyond three mismatch
lines, prefer splitting it into multiple focused examples so reviewers do not
lose the identity/capability/error-class distinctions inside one dense block.

Split by comparison axis rather than by severity. For example, separate
identity-field failures from capability-field failures and keep result-class
examples distinct from shape-only examples. Severity ordering still matters in
review writeups, but the examples here should primarily teach field-family
interpretation.

Canonical example families:

- identity mismatch family
  - `node`
  - `id`
- capability mismatch family
  - `action`
  - `cancellable`
- result-class mismatch family
  - known vs unknown task lookup
  - cancellable vs non-cancellable cancellation result
- shape-only mismatch family
  - required field present but wrong envelope shape
  - required field present but wrong nesting level
  - representative fields:
    - `node` for wrong envelope placement
    - `action` for wrong nesting or serialization shape
  - comparison output examples:
    - `required parity mismatch: node (shape mismatch)`
    - `required parity mismatch: action (shape mismatch)`

For `Phase A`, keep `shape mismatch` as the shared canonical phrase for these
cases. Do not split it further unless Steelsearch starts distinguishing stable
subclasses such as envelope-level versus nesting-level mismatches in automated
comparison output.

If reviewers need that extra distinction today, express it only in the
free-form boundary note, not by inventing a second canonical shape-mismatch
phrase.

Canonical free-form note vocabulary for shape-only mismatch:

- `envelope-level shape mismatch`
- `nesting-level shape mismatch`

Do not shorten these to just `envelope-level` or `nesting-level`. Without the
shared `shape mismatch` anchor, the note stops clearly signaling that the issue
is structural rather than semantic or result-class related.

Freeze this vocabulary for `Phase A`. Keep `envelope-level shape mismatch` and
`nesting-level shape mismatch` as the canonical free-form note terms unless a
broader mismatch-taxonomy pass introduces a stable alternative across API
families.
```

## Cat And Operational Convenience APIs

| Route family | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| `/_cat/indices`, `/_cat/plugins`, related cat APIs | Human-oriented text or JSON summaries for operators. | Some cat-compatible outputs exist for development comparison, but formatting and coverage are intentionally partial. | Partial |
| Repository, decommission, remote-store, tiering, workload management admin routes | Production operations surfaces used by OpenSearch clusters. | Present in OpenSearch source inventory. Most remain unimplemented in Steelsearch. | Planned |

## Notes

- Steelsearch currently treats many operational APIs as compatibility shells for
  development replacement, not as release-grade operational contracts.
- Production replacement still requires completion of discovery, task queues,
  allocation semantics, node telemetry depth, and readiness gates.
