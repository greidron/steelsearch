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
| Propagation model | `parent_task_id` child cancellation visibility includes same-node, cross-node, and background-worker descendant propagation; spawned-worker rethrottle propagation remains intentionally independent rather than inherited |
| Terminal-state accounting | acknowledged/failed cluster-manager task records remain queryable through `GET /_tasks*` without contributing to pending queue depth, with bounded per-bucket retention/eviction, stale cancellation-marker pruning, persisted restart readback, cancelled-task completion plus partial-progress status readback until eviction, and cancelled-terminal restart-sync/live-shutdown/node-role-transition refusal with progress preservation |
| Queue interaction | queued cancellation state and in-flight refusal are visible through task and pending-task routes, including active queued/in-flight node-role-transition cancellation/refusal; worker-owned drain/refusal ordering is still bounded |
| Restart interaction | shared-runtime restart readback preserves task queue state and cancelled ids, keeps accepted in-flight tasks visible without queued replay, refuses cancelling those in-flight records, preserves cancelled-terminal progress when cancel is refused after restart sync, live shutdown, or node-role transition, preserves active queued/in-flight task cancellation/refusal across node-role transition, preserves task listing/cancel continuity when per-request sync sees a partial shared-state recovery error, and accepts cancel requests after per-request shared-runtime sync on restart |
| Error classification | route-level `404`, bounded repeated-cancel success, in-flight refusal, completion-race terminal refusal without cancelled-marker pollution, and cancelled-terminal restart-sync/live-shutdown/node-role-transition refusal exist |

### Required tests

- add fixture-backed distinction for:
  - queued cancellation versus worker drain races;
- add operator-visible evidence for terminal-state retention:
  - broader node-role transition retention beyond cancelled-terminal
    visibility/refusal and the current completion/restart/live-shutdown/eviction
    coverage.

### Required implementation

- introduce an explicit cancellation coordinator or equivalent runtime owner for
  task state transitions.
- tie queued-task cancellation into in-flight worker ownership and drain ordering.
- define worker-drain contracts for `GET /_tasks*` beyond the current
  acknowledged/failed terminal eviction bound, stale cancellation-marker
  pruning, and completion/progress/restart/live-shutdown, node-role-transition,
  and eviction readback.
- tie cancellation state into shutdown-window and partial-recovery handling
  rather than treating those paths as stateless route-level responses.

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
| Rethrottle sequencing | repeated rethrottle calls have last-write-wins readback evidence, but races with task completion are still open |
| Parent-child propagation | same-node parent/child and multi-level descendant rethrottle rate readback is independent without implicit propagation, but cross-node and spawned worker sub-task propagation remain open |
| Persistence and restart | shared-runtime restart readback preserves requested throttle rates, and rethrottle requests are accepted after per-request shared-runtime sync on restart; shutdown-window and partial-recovery behavior remain open |
| Admission and backpressure interaction | there is no documented relationship between throttle state, queue admission, backlog growth, and overload refusal |
| Terminal-state behavior | rethrottle-after-cancel and rethrottle-after-terminal-task are rejected without mutating rate state, but rethrottle-during-shutdown remains open |

### Required tests

- add fixture-backed distinction for:
  - cross-node parent task rethrottle versus sliced child work visibility;
  - rethrottle race-with-completion behavior.
- add restart-smoke coverage for:
  - rethrottle request during shutdown or partial-recovery windows beyond the
    current per-request sync-on-restart guard.
- add operator-visible evidence for:
  - whether the last requested throttle rate is observable;
  - whether cross-node child work inherits or diverges from the parent rate;
  - whether overload/backpressure changes task admission under throttling.

### Required implementation

- introduce an explicit runtime owner for throttle rate state rather than
  treating rethrottle as a stateless route response.
- define race-with-finish states beyond the current repeated rethrottle
  last-write-wins route evidence.
- connect throttle state to child-work orchestration for sliced tasks.
- define shutdown-window and partial-recovery throttle behavior beyond the
  current shared-runtime restart readback and per-request sync-on-restart guard.

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
| Queue ownership | search/write, maintenance, snapshot, cluster-reroute, and task-submission route admission now have active-slot queue waiting and drain evidence, but terminal long-running task lifecycle ownership is still bounded |
| Admission control | search/write, maintenance, snapshot, cluster-reroute, and task-submission routes now have bounded queue-full refusal and queued execution evidence, mixed search/maintenance and write/maintenance backlog drain independently, and runtime thread-pool queue/counter state resets after shared-runtime restart; accepted in-flight task readback/refusal, accepted queued task-submission no-replay after shared-runtime restart and partial shared-state recovery errors, partial-recovery task-submission refusal, live-shutdown task-submission refusal, partial shared-state recovery error task-listing/cancel continuity, multi-node queued/in-flight task visibility with remote node metadata, remote task backlog admission isolation for task-submission and local search/write routes, and local overload counter isolation from remote task metadata are covered, while broader multi-node fairness contracts are still missing |
| Backpressure propagation | there is no contract for how overload feeds back into reroute, maintenance, snapshot, or task-submission routes |
| Priority and fairness | there is no evidence for task class prioritisation, starvation avoidance, or separation between user-facing writes and maintenance work |
| Queue visibility | `pending_tasks` surfaces exist and now preserve remote node metadata for multi-node queued/in-flight task records, local task submission remains admissible under remote-only backlog, and `_nodes/stats` no longer copies local overload counters onto remote nodes, but the production mapping between visible entries and real internal queue owners remains bounded |
| Restart and drain behavior | runtime thread-pool queue/counter state is proven ephemeral across shared-runtime restart, accepted queued task-submission work is not replayed into a restarted runtime view or during partial shared-state recovery errors, and new task-submission admission is refused while partial shared-state recovery is incomplete or live shutdown is in progress; node-role transitions remain open |

### Required tests

- add fixture-backed distinction for:
  - empty queue versus non-empty queue visibility;
  - queued reroute/maintenance work versus immediately executed work;
  - overload refusal versus accepted-but-pending behavior.
- add harness coverage for:
  - burst submission of maintenance/task-control requests;
  - pending-task visibility during backlog growth;
  - backlog drain after load subsides beyond the current bounded single-node
    route admission guards.
- add restart-smoke coverage for node-role transitions.

### Required implementation

- introduce an explicit queue owner for cluster-manager tasks, maintenance work,
  and other background admission-controlled actions.
- extend overload thresholds and refusal semantics beyond the current bounded
  route admission guards, mixed-class drain evidence for search/write versus
  maintenance, and remote-backlog
  task-submission/search/write admission isolation into broader multi-node
  fairness behavior.
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
