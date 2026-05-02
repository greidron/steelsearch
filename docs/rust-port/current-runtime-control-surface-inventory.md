# Current Runtime Control Surface Inventory

This document inventories the operator-visible runtime control surface currently
exposed by the standalone runtime. It is not a completeness claim. Its purpose
is to separate what operators can already hit over REST from the internal
runtime-control gaps that still remain.

## Reading Rules

- `operator-visible surface` means a REST route or documented control entrypoint
  an operator can invoke today.
- `current evidence` points to the documentation or generated evidence family
  already tracking the surface.
- `internal gap` explains what deeper runtime/thread-pool/scheduler behavior is
  still missing even when the route exists.

## Inventory

| Control family | Representative operator-visible surface | Current evidence | Internal gap still open |
| --- | --- | --- | --- |
| Task inspection | `GET /_tasks`, `GET /_tasks/{task_id}`, `GET /_cluster/pending_tasks`, `GET /_cat/pending_tasks` | `docs/api-spec/generated/route-evidence-matrix.md` `root-cluster-node` rows | no authoritative task resource tracking service, queue accounting, or production-grade scheduler ownership |
| Task cancellation / throttling | `POST /_tasks/_cancel`, `POST /_tasks/{task_id}/_cancel`, `POST /_tasks/{task_id}/_rethrottle` | stateful route evidence plus authz fixture planning | no authoritative cancellation lifecycle, backpressure model, or throttling scheduler semantics |
| Search session control | `POST|GET|DELETE /_search/scroll`, `POST /{index}/_search/point_in_time`, `DELETE /_search/point_in_time*` | `docs/api-spec/search.md` and generated route evidence | partial session bookkeeping; no deeper runtime service guarantees for resource accounting |
| Tier / maintenance control | `POST /_tier/_cancel/*`, `POST /{index}/_tier/*`, `POST /_refresh`, `POST /_flush`, `POST /_cache/clear`, `POST /_forcemerge` | `document-and-bulk.md`, generated route evidence, semantic probes | route-level behavior exists but not full background task/service lifecycle or queue semantics |
| Snapshot control | `PUT|GET|DELETE /_snapshot/{repo}`, `POST /_snapshot/{repo}/_cleanup`, `POST /_snapshot/{repo}/{snapshot}/_restore`, `POST /_snapshot/{repo}/_verify` | `snapshot-migration-interop.md`, generated route evidence | no authoritative long-running snapshot worker model or full runtime coordination service |
| Cluster health / reroute control | `GET /_cluster/health*`, `POST /_cluster/reroute`, `GET|PUT /_cluster/settings` | `root-cluster-node` docs and generated evidence | cluster-service semantics, reroute batching, publication/apply coordination remain partial |
| Close / open / stateful maintenance | `POST /_close`, `POST /_open`, related targeted variants | semantic probes and index-metadata evidence | no deeper node lifecycle scheduler or recovery orchestration behind the route surface |
| Security harness control entrypoint | `tools/run-security-compat-harness.sh` | `docs/api-spec/README.md` security harness section | harness exists, but runtime-owned authn/authz service lifecycle and audit plumbing remain partial |

## Immediate Mapping Follow-up

The next runtime-control tasks should map each family above to the missing
internal subsystems, especially:

1. task cancellation and throttling;
2. queue/backpressure ownership;
3. maintenance task lifecycle;
4. thread-pool API presence versus explicit out-of-scope classification.

## Operator Surface To Internal Gap Mapping

| Operator-visible family | Missing internal owner / subsystem | Concrete gap to close next |
| --- | --- | --- |
| Task inspection | `TaskResourceTrackingService` equivalent | authoritative task registry, task-resource accounting, queue/owner metadata |
| Task cancellation / throttling | task scheduler + cancellation coordinator | cancellation propagation, throttle state ownership, backpressure-aware task control |
| Search session control | scroll/PIT lifecycle manager | session leasing, expiry, resource accounting, cleanup guarantees |
| Tier / maintenance control | background maintenance scheduler | queued maintenance ownership, backpressure, retry/failure lifecycle |
| Snapshot control | snapshot worker/coordinator | long-running worker lifecycle, progress ownership, restore/cleanup coordination |
| Cluster health / reroute control | `ClusterService` + reroute batching layer | publication/apply ordering, reroute queueing, state transition ownership |
| Close / open / maintenance state transitions | recovery/orchestration manager | close/open sequencing, recovery gating, maintenance side effects |
| Security harness control entrypoint | authn/authz runtime services | runtime-owned credential validation, audit emission, redaction-aware failure handling |

## Lifecycle Work Items Split

| Work item | Primary surface | Internal concern to isolate next |
| --- | --- | --- |
| Task cancellation lifecycle | `POST /_tasks/_cancel*` | cancellation ownership, propagation timing, terminal-state accounting |
| Throttling lifecycle | `POST /_tasks/{task_id}/_rethrottle` | throttle token ownership, rethrottle sequencing, task rate-state persistence |
| Queue / backpressure lifecycle | pending tasks, background maintenance entrypoints | queue depth ownership, admission control, overload refusal semantics |
| Maintenance task lifecycle | refresh/flush/cache-clear/forcemerge, tier transitions, snapshot cleanup/restore | background worker ownership, retry/failure state, cleanup guarantees |

## Task Cancellation Lifecycle Gap

### Operator-visible surfaces

- `POST /_tasks/_cancel`
- `POST /_tasks/{task_id}/_cancel`
- task-adjacent state readback:
  - `GET /_tasks`
  - `GET /_tasks/{task_id}`
  - `GET /_cluster/pending_tasks`

### Current evidence

- stateful semantic probes already distinguish:
  - unknown task;
  - known non-cancellable task;
  - known cancellable task path shape.
- generated/runtime evidence shows the route family exists and responds with
  bounded OpenSearch-like envelopes.
- authz coverage already treats task-admin routes as admin-only high-risk
  surfaces.

### Internal lifecycle gaps still open

| Gap class | Why the current surface is insufficient |
| --- | --- |
| Cancellation ownership | there is no authoritative runtime-owned cancellation coordinator that owns who may flip a task from running to cancelling to cancelled |
| Propagation model | current route evidence does not prove cancellation reaches all task kinds, child work, or background workers in a deterministic order |
| Terminal-state accounting | there is no authoritative contract for whether a cancelled task remains queryable, when it disappears from task listings, or how partial progress is reported |
| Queue interaction | there is no explicit distinction between cancelling queued work versus cancelling already-running work, and no refusal/backpressure interaction is documented |
| Restart interaction | there is no evidence for what happens when cancellation is requested near shutdown, restart, or partial persisted-state recovery |
| Error classification | route-level `404`/bounded success exists, but not a full matrix for already-finished, already-cancelled, or race-with-completion states |

### Required tests

- add fixture-backed distinction for:
  - queued-versus-running cancellation;
  - already-finished-versus-already-cancelled task ids;
  - parent task cancel versus child task visibility;
  - repeated cancel idempotency with post-cancel readback.
- add restart-smoke coverage for:
  - cancel-before-shutdown;
  - cancel-during-restart;
  - post-restart task listing continuity.
- add operator-visible evidence for terminal-state readback:
  - whether cancelled tasks remain listable;
  - whether partial progress fields are stable;
  - whether cancellation removes or mutates pending-task visibility.

### Required implementation

- introduce an explicit cancellation coordinator or equivalent runtime owner for
  task state transitions.
- separate queued-task cancellation from in-flight worker cancellation.
- define terminal task states and their visibility contract for `GET /_tasks*`.
- tie cancellation state into restart/recovery handling rather than treating it
  as a stateless route-level response.

### Immediate follow-up

1. document the throttling lifecycle separately so cancellation and rate-state
   ownership do not stay conflated.
2. document queue/backpressure semantics separately so queued-task cancellation
   has a clear owner.
3. add restart-smoke backlog entries once the node restart harness exists.

## Throttling Lifecycle Gap

### Operator-visible surfaces

- `POST /_tasks/{task_id}/_rethrottle`
- task-adjacent state readback:
  - `GET /_tasks`
  - `GET /_tasks/{task_id}`
- by-query and reindex task families that expose rethrottle paths:
  - `/_reindex`
  - `/{index}/_update_by_query`
  - `/{index}/_delete_by_query`

### Current evidence

- stateful semantic probes already distinguish:
  - known task rethrottle path;
  - unknown task path;
  - non-cancellable versus task-shaped route handling.
- generated/runtime evidence shows the rethrottle route family exists and
  returns bounded envelopes.
- document-write semantic fixtures already cover reindex and by-query task
  families at route/summary level.

### Internal lifecycle gaps still open

| Gap class | Why the current surface is insufficient |
| --- | --- |
| Rate-state ownership | there is no authoritative runtime owner for throttle tokens, target rates, or the effective rate currently applied to a running task |
| Rethrottle sequencing | current evidence does not prove ordered behavior for repeated rethrottle calls, last-write-wins semantics, or races with task completion |
| Parent-child propagation | there is no contract for whether rethrottle affects only a parent task, all child slices, or spawned worker sub-tasks consistently |
| Persistence and restart | there is no evidence for whether throttle state survives restart, is recomputed, or is dropped during recovery |
| Admission and backpressure interaction | there is no documented relationship between throttle state, queue admission, backlog growth, and overload refusal |
| Terminal-state behavior | route-level errors exist, but not a full matrix for rethrottle-after-finish, rethrottle-after-cancel, or rethrottle-during-shutdown |

### Required tests

- add fixture-backed distinction for:
  - repeated rethrottle on the same task id;
  - rethrottle before task completion versus after task completion;
  - parent task rethrottle versus sliced child work visibility;
  - rethrottle followed by task readback to confirm stable effective rate.
- add restart-smoke coverage for:
  - throttled task before shutdown;
  - throttle state after restart;
  - rethrottle request during restart window.
- add operator-visible evidence for:
  - whether the last requested throttle rate is observable;
  - whether child work inherits or diverges from the parent rate;
  - whether overload/backpressure changes task admission under throttling.

### Required implementation

- introduce an explicit runtime owner for throttle rate state rather than
  treating rethrottle as a stateless route response.
- define sequencing semantics for repeated rethrottle calls and race-with-finish
  states.
- connect throttle state to child-work orchestration for sliced tasks.
- decide whether throttle state is persisted, recomputed, or discarded across
  restart and recovery, and expose that contract.

### Immediate follow-up

1. document queue/backpressure semantics separately so rethrottle can be tied to
   admission-control behavior instead of only route-level envelopes.
2. document maintenance task lifecycle separately so background work that is not
   task-id-addressable has an explicit owner.
3. add restart-smoke backlog entries once the node restart harness exists.

## Queue / Backpressure Gap

### Operator-visible surfaces

- queue-adjacent readback:
  - `GET /_cluster/pending_tasks`
  - `GET /_cat/pending_tasks`
  - `GET /_tasks`
- maintenance and state-mutation entrypoints that should eventually be governed
  by admission control:
  - `POST /_cluster/reroute`
  - `POST /_refresh`
  - `POST /_flush`
  - `POST /_cache/clear`
  - `POST /_forcemerge`
  - snapshot cleanup/restore entrypoints

### Current evidence

- generated route evidence confirms pending-task readback surfaces exist.
- stateful/admin semantic probes already exercise:
  - task inspection;
  - reroute route shape;
  - maintenance entrypoint envelopes.
- current docs distinguish operator-visible task and maintenance routes from the
  deeper runtime services they would need in production.

### Internal lifecycle gaps still open

| Gap class | Why the current surface is insufficient |
| --- | --- |
| Queue ownership | there is no authoritative runtime-owned queue model for pending cluster-manager work, maintenance work, or long-running task admission |
| Admission control | current evidence does not prove any overload threshold, refusal policy, or bounded queueing behavior when the runtime is saturated |
| Backpressure propagation | there is no contract for how overload feeds back into reroute, maintenance, snapshot, or task-submission routes |
| Priority and fairness | there is no evidence for task class prioritisation, starvation avoidance, or separation between user-facing writes and maintenance work |
| Queue visibility | `pending_tasks` surfaces exist, but there is no authoritative mapping between visible entries and the real internal queue owners or queue depth |
| Restart and drain behavior | there is no evidence for what queued work does on shutdown, restart, partial recovery, or node-role transitions |

### Required tests

- add fixture-backed distinction for:
  - empty queue versus non-empty queue visibility;
  - queued reroute/maintenance work versus immediately executed work;
  - overload refusal versus accepted-but-pending behavior.
- add harness coverage for:
  - burst submission of maintenance/task-control requests;
  - pending-task visibility during backlog growth;
  - backlog drain after load subsides.
- add restart-smoke coverage for:
  - queued work before shutdown;
  - queue state after restart;
  - refusal versus replay behavior during recovery.

### Required implementation

- introduce an explicit queue owner for cluster-manager tasks, maintenance work,
  and other background admission-controlled actions.
- define overload thresholds and refusal semantics instead of exposing only
  success-shaped route envelopes.
- connect visible pending-task surfaces to authoritative internal queue state.
- define restart/drain handling for queued work rather than leaving it implicit.

### Immediate follow-up

1. document maintenance task lifecycle separately so background work owners and
   retry/failure semantics are distinct from generic queue ownership.
2. classify thread-pool API coverage explicitly so queue/backpressure work is
   not conflated with missing thread-pool observability.
3. add load-oriented harness entries once restart and multi-node smoke scripts
   exist.

## Maintenance Task Lifecycle Gap

### Operator-visible surfaces

- index-maintenance entrypoints:
  - `POST /_refresh`
  - `POST /_flush`
  - `POST /_cache/clear`
  - `POST /_forcemerge`
  - targeted index variants of the same routes
- tier and maintenance-state entrypoints:
  - `POST /{index}/_tier/*`
  - `POST /_tier/_cancel/*`
  - `POST /_open`
  - `POST /_close`
- snapshot-maintenance entrypoints:
  - `POST /_snapshot/{repo}/_cleanup`
  - `POST /_snapshot/{repo}/{snapshot}/_restore`

### Current evidence

- semantic probes already cover:
  - selector expansion for refresh/flush/cache-clear/forcemerge;
  - repeated close/open idempotency;
  - tier set/cancel route behavior;
  - snapshot cleanup/restore bounded envelopes and missing-repository failures.
- admin semantic compat fixtures already include:
  - cleanup semantics;
  - tier cancel/readback shape;
  - selector-based maintenance surfaces.

### Internal lifecycle gaps still open

| Gap class | Why the current surface is insufficient |
| --- | --- |
| Worker ownership | there is no authoritative background worker owner for accepted maintenance work once the REST route returns |
| Retry and failure policy | current evidence does not prove whether failed maintenance work is retried, abandoned, or surfaced through an observable task/error channel |
| Progress visibility | there is no operator-visible contract for in-progress, partially-applied, or completed maintenance state beyond bounded immediate response envelopes |
| Cross-surface coordination | there is no contract for how tier changes, close/open, refresh/flush, and snapshot restore interact when they overlap on the same index or data stream |
| Cleanup guarantees | there is no evidence for whether accepted maintenance work guarantees cleanup of temporary state, leases, or intermediate markers after failure |
| Restart interaction | there is no evidence for whether maintenance work is resumed, rolled back, or forgotten across shutdown and restart |

### Required tests

- add fixture-backed distinction for:
  - accepted maintenance request versus completed maintenance effect;
  - repeated maintenance calls while prior work is still logically in flight;
  - overlapping maintenance operations on the same target.
- add restart-smoke coverage for:
  - maintenance work accepted before shutdown;
  - tier transition interrupted by restart;
  - snapshot cleanup/restore interrupted by restart.
- add operator-visible evidence for:
  - post-operation readback showing completion or rollback;
  - failure-path visibility when cleanup is partial;
  - interaction between close/open state and other maintenance routes.

### Required implementation

- introduce explicit runtime owners for background maintenance work rather than
  treating each route as a synchronous envelope producer.
- define retry, failure, and cleanup policy for each maintenance family.
- connect maintenance completion state to operator-visible readback surfaces.
- define restart semantics for accepted-but-not-finished maintenance work.

### Immediate follow-up

1. classify thread-pool API coverage explicitly so maintenance work is not
   conflated with missing thread-pool observability.
2. add startup-ordering and restart-harness evidence once those harnesses
   exist, because maintenance lifecycle and restart behavior are coupled.
3. split per-family maintenance follow-up later if one family diverges
   materially from the rest.

## Thread-Pool API Coverage Classification

Thread-pool observability and control should not stay implicit. The current
runtime-control surface does not yet claim a first-class thread-pool API family,
so the gap needs an explicit status per replacement profile.

| Surface / expectation | Current status | Classification | Why |
| --- | --- | --- | --- |
| thread-pool stats/inspection routes | no first-class route inventoried in current standalone runtime evidence | out-of-scope for current standalone profile | the current standalone claim is bounded around REST compatibility and semantic route behavior, not production-grade scheduler observability |
| thread-pool queue depth and rejection counters | no authoritative runtime surface | planned route / planned evidence for replacement-ready claims | queue/backpressure and overload claims are not defensible without observable queue depth and rejection state |
| per-pool active/idle worker accounting | no authoritative runtime surface | planned route / planned evidence for secure standalone and beyond | maintenance, throttling, and cancellation lifecycle work all need worker ownership visibility to become production claims |
| operator-visible thread-pool tuning controls | no first-class runtime route or documented local control | out-of-scope for current phase, planned only if operator model expands | adding tuning without authoritative scheduler ownership would create misleading control surfaces |

### Current interpretation

- do not treat missing thread-pool routes as accidental omissions in the
  current standalone profile.
- do treat them as replacement blockers for any claim that depends on queue
  visibility, overload evidence, or scheduler introspection.

### Required follow-up

- if a replacement profile starts claiming overload/backpressure guarantees,
  add planned route/evidence entries for thread-pool and queue introspection at
  the same time.
- if thread-pool routes remain absent, keep them explicitly documented as
  out-of-scope rather than leaving them implied by unrelated task routes.
