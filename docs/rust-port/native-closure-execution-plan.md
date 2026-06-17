# Native Closure Execution Plan

This plan tracks the remaining non-native work after excluding OpenSearch
response-shape compatibility, OpenSearch snapshot-file compatibility, and
binary-to-binary Lucene compatibility.

## Scope

In scope:

- source-backed query and aggregation execution that can still force document
  scans or full hit materialization;
- vector and hybrid search paths that still need broader direct native
  page/window and aggregation coverage;
- mixed-cluster shard movement hardening where the representative happy path is
  already evidenced, but interruption/retry/restart evidence is still thin;
- production runtime controls and production security enforcement.

Out of scope:

- OpenSearch-shaped error envelopes, field names, headers, and response
  formatting;
- direct OpenSearch snapshot restore;
- Lucene segment or translog binary compatibility.

## Current Evidence Baseline

- Search compatibility profile has no remaining failed `search-compat` or
  `search-strict` cases in the latest recorded report.
- Benchmark matrix for `minilm-knn` shows SteelSearch faster than OpenSearch in
  the latest local run, with lower RSS peak in both one-node and three-node
  topologies.
- Mixed Java/OpenSearch shard movement has a representative live probe covering
  Java primary to SteelSearch replica, SteelSearch primary promotion, Java
  replica rejoin, and failback to Java. The probe now records shard checkpoint
  drift and requires zero drift.
- Native-closure runtime validation now has a guarded compact runner,
  `tools/run-native-closure-validation.py --batch compact`, that rejects
  zero-test matches. The compact batch passed on 2026-06-17 with 8/8 tests:
  four malformed wrapper placeholder seats (`bucket_sort`, `derivative`,
  `serial_diff`, `bucket_count`) and four multi-index `date_histogram`
  rebucketing wrapper seats for the same wrapper shapes.
- The same guarded runner now has a `rebucketing-wide` batch. It passed on
  2026-06-17 with 12/12 tests and `zero_tests=0`, covering the same wrapper
  shapes across `auto_date_histogram`, `histogram`, and
  `variable_width_histogram` multi-index rebucketing seats.
- The guarded runner also has a `vector-knn` batch. It passed on 2026-06-17
  with 7/7 tests and `zero_tests=0`, covering filtered KNN scoring, runtime
  cache bounds/invalidation, single-index vector-native page plus aggregation
  fetch, multi-index vector-native page plus aggregation reduce, and `_id`,
  `_score`, and fast-field sort reduce variants.
- The same runner now has a `startup-preflight` batch. It passed on 2026-06-17
  with 12/12 tests and `zero_tests=0`, covering data-path, bind, duplicate
  node-id, invalid address/port, role/bootstrap, structured production
  security/release policy gates, production-mode gate, and daemon-level
  data-path / occupied-port refusal cases.
- The same runner now has a `startup-readiness` batch. It passed on 2026-06-17
  with 2/2 tests and `zero_tests=0`, covering shared startup preflight and
  readiness blocker reasons for concrete filesystem refusal plus production
  security/release gate refusal.
- The same runner now has a `runtime-tasks` batch. It passed on 2026-06-17
  with 19/19 tests and `zero_tests=0`, covering task cancellation through
  runtime-local state mutation plus follow-up task readback for both query-param
  and path task-id cancellation forms, repeated cancel idempotency with
  post-cancel readback, parent-task-id child cancellation visibility including
  same-node, cross-node, and background-worker descendant propagation,
  queued-versus-in-flight cancellation distinction, completion-race refusal
  without cancelled-marker pollution, and acknowledged/failed terminal task readback
  without polluting pending-task queue depth, plus
  bounded terminal task retention/eviction with stale cancellation-marker
  pruning, cancelled-task completion and partial-progress status readback through
  restart until eviction, cancelled-terminal restart-sync, live-shutdown, and
  node-role-transition refusal with progress preservation, persisted restart
  readback, active queued/in-flight node-role-transition cancellation/refusal,
  and shared-runtime restart readback for task queue state and cancelled task
  ids, including accepted in-flight task readback/refusal without queued replay,
  partial shared-state recovery error task-listing/cancel continuity, and cancel requests accepted during the
  per-request shared-runtime sync window after restart.
- The same runner now has a `runtime-queue` batch. It passed on 2026-06-17
  with 4/4 tests and `zero_tests=0`, covering runtime task queue metadata plus
  shared queue-depth visibility across cluster health, `_tasks`, cluster pending
  tasks, cat pending tasks, cat thread-pool, and node-stats thread-pool routes,
  including queued cancellation state versus in-flight execution visibility and
  multi-node queued/in-flight task visibility with remote node metadata.
- The same runner now has a `runtime-backpressure` batch. It passed on
  2026-06-17 with 15/15 tests and `zero_tests=0`, covering administrative
  thread-pool active/queued telemetry derived from the same runtime task queue
  state plus search/write thread-pool completion counters derived from real
  search and bulk route execution across success and request-error paths,
  active-slot queue waiting/drain under concurrent search/write requests,
  independent mixed search/maintenance backlog drain, remote task backlog not
  blocking local task-submission admission or local search/write admission, and
  bounded queue-full rejection for saturated search/write pools, plus
  maintenance refresh/flush/cache-clear/forcemerge admission through the same
  runtime-owned waiting and rejection model, and snapshot create/restore/cleanup
  admission plus cluster reroute admission through the same runtime-owned
  waiting and rejection model, and by-query/reindex task-submission admission
  through the same runtime-owned waiting and rejection model, accepted queued
  task-submission no-replay across shared-runtime restart and partial
  shared-state recovery errors, partial-recovery task-submission refusal, plus
  live-shutdown task-submission refusal, plus restart reset evidence for
  runtime thread-pool queue/counter state.
- The same runner now has a `runtime-throttle` batch. It passed on 2026-06-17
  with 7/7 tests and `zero_tests=0`, covering by-query rethrottle state
  mutation from both query-parameter and request-body rates, repeated
  last-write-wins rethrottle sequencing, follow-up `/_tasks` list/get readback,
  shared-runtime restart readback for requested throttle rates, and rejection
  for cancelled or terminal tasks without mutating rate state, plus same-node
  parent/child and multi-level descendant rethrottle rate readback without
  implicit rate propagation and rethrottle requests accepted during the
  per-request shared-runtime sync window after restart.
- The same runner now has a `runtime-task-metadata` batch. It passed on
  2026-06-17 with 4/4 tests and `zero_tests=0`, covering runtime parent task
  metadata preservation through `/_tasks/{task_id}`, `_cat/tasks`, and the
  bounded task route surface, plus parent grouping normalization coverage.
- The same runner now has a `runtime-task-headers` batch. It passed on
  2026-06-17 with 2/2 tests and `zero_tests=0`, covering persisted
  `x-opaque-id` task header readback through `/_tasks`, `/_tasks/{task_id}`,
  task cancellation, and `_cat/tasks` JSON rows.
- The same runner now has a `runtime-task-children` batch. It passed on
  2026-06-17 with 8/8 tests and `zero_tests=0`, covering same-node
  `/_tasks?group_by=parents` child nesting from runtime task state plus
  parent-task-id child cancellation visibility, same-node multi-level
  descendant cancellation propagation, cross-node descendant cancellation
  propagation, background-worker descendant cancellation propagation, and
  same-node parent/child plus multi-level descendant
  rethrottle rate visibility.

## Workstreams

### 1. Source-Backed Query And Aggregation Closure

Goal: reduce paths that must evaluate from `_source` or materialized
`SearchHit` values before returning results.

Initial targets:

1. keep an explicit inventory of source-backed query families:
   `nested`, `geo_distance`, `distance_feature`, `rank_feature`,
   `more_like_this`, `terms_set`, phrase/prefix/bool-prefix queries,
   `combined_fields`, `multi_match`, `query_string`, and
   `simple_query_string`;
2. record which of those families have native candidate-set narrowing versus
   full document scan fallback;
3. add benchmark counters or report rows for materialized-hit fallback usage;
4. promote one high-traffic family at a time from source-backed scan to native
   candidate narrowing when the Tantivy surface supports it.

Current narrowed families:

- `nested` exact scalar leaves: child ordinal indexes now narrow term/terms and
  supported bool nested leaves before parent document lookup. Unsupported nested
  shapes still use the explicit source-validation fallback.
- `terms_set` exact scalar leaves: Tantivy minimum-should-match query builders
  and native candidate helpers cover scalar keyword/tag-style terms before
  source fallback is needed.
- `rank_feature` positive numeric/bool leaves and `distance_feature`
  numeric/date field-presence leaves: Tantivy native builders and hybrid
  candidate helpers cover the filter-like narrowing subset, while richer
  scoring/parity shapes remain fallback-visible.
- `geo_distance` geo-point leaves, `more_like_this` explicit-field token
  overlap, and `query_string` / `simple_query_string` tokenized text/keyword
  field sets: Tantivy native builders and hybrid candidate helpers cover
  candidate narrowing, while exact geo validation, fieldless/analyzer-sensitive
  token overlap, and broad parser fallback shapes remain telemetry-visible.

Exit evidence:

- `tools/report-non-native-paths.py` reports the family as native or
  native-candidate-narrowed;
- unit tests cover the native path and fallback boundary;
- benchmark report shows no regression for the affected query family.

### 2. Vector And Hybrid Direct-Path Expansion

Goal: keep vector and hybrid workloads on native candidate/page/window paths
instead of returning to broad document materialization.

Initial targets:

1. enumerate vector/hybrid shapes with direct paths:
   pure `knn`, constrained `knn`, direct-path bool hybrid, explicit sort,
   `size=0`, native aggregation collection, and multi-index reduce;
2. add report rows for shapes that still fall back to materialized response
   helpers;
3. add focused regression cases for hybrid plus aggregation plus explicit sort;
4. only widen native paths when result ordering and total-hit semantics are
   already proven.

Exit evidence:

- query-shape report shows direct vector/hybrid path use for each promoted
  shape;
- E2E semantic comparison remains green;
- benchmark matrix keeps vector and hybrid throughput within the accepted
  envelope.

Validation runner:

- `tools/run-native-closure-validation.py --batch compact` must report
  `failed_count == 0` and `zero_test_count == 0` before treating the compact
  malformed-wrapper / `date_histogram` rebucketing slice as runtime evidence.
- `tools/run-native-closure-validation.py --batch rebucketing-wide` must also
  report `failed_count == 0` and `zero_test_count == 0` before treating the
  widened `auto_date_histogram`, `histogram`, and `variable_width_histogram`
  rebucketing-wrapper slice as runtime evidence.
- `tools/run-native-closure-validation.py --batch vector-knn` must report
  `failed_count == 0` and `zero_test_count == 0` before treating the direct
  vector/KNN page, aggregation, cache, and sort slices as runtime evidence.
- `tools/run-native-closure-validation.py --batch startup-preflight` must
  report `failed_count == 0` and `zero_test_count == 0` before treating the
  concrete startup refusal slice and structured production security/release
  gate as runtime-control evidence.
- `tools/run-native-closure-validation.py --batch startup-readiness` must
  report `failed_count == 0` and `zero_test_count == 0` before treating shared
  startup/readiness blocker reasons, including production security/release gate
  blockers, as runtime-control evidence.
- `tools/run-native-closure-validation.py --batch runtime-tasks` must report
  `failed_count == 0` and `zero_test_count == 0` before treating task
  cancellation, repeated cancel idempotency, parent-task-id child cancellation,
  same-node, cross-node, and background-worker descendant cancellation propagation,
  queued-versus-in-flight cancellation distinction, completion-race refusal
  without cancelled-marker pollution, terminal-state task readback, bounded
  terminal retention/eviction, stale cancellation-marker pruning, cancelled-task
  completion and partial-progress status readback through restart until eviction,
  cancelled-terminal restart-sync, live-shutdown, and node-role-transition
  refusal with progress preservation, active queued/in-flight
  node-role-transition cancellation/refusal, and pending-depth separation as
  runtime-control evidence, including shared-runtime restart readback for task
  queue state and cancelled ids, accepted in-flight
  task readback/refusal without queued replay, partial shared-state recovery
  error task-listing/cancel continuity, plus cancel-request handling during the
  per-request sync window after restart.
- `tools/run-native-closure-validation.py --batch runtime-queue` must report
  `failed_count == 0` and `zero_test_count == 0` before treating task queue
  depth, pending-task metadata, pending-task cancellation visibility, and
  multi-node remote task metadata visibility as runtime-control evidence.
- `tools/run-native-closure-validation.py --batch runtime-backpressure` must
  report `failed_count == 0` and `zero_test_count == 0` before treating
  administrative and search/write workload thread-pool telemetry plus
  active-slot queue waiting/drain, independent mixed search/maintenance backlog
  drain, remote task backlog admission isolation for task-submission and local
  search/write routes, queue-full rejection, and
  maintenance route plus snapshot/cluster-manager/task-submission route admission as
  runtime-control evidence, including accepted queued task-submission no-replay
  across shared-runtime restart and partial shared-state recovery errors, and
  partial-recovery task-submission refusal, live-shutdown task-submission
  refusal, and runtime thread-pool queue/counter reset after shared-runtime
  restart.
- `tools/run-native-closure-validation.py --batch runtime-throttle` must report
  `failed_count == 0` and `zero_test_count == 0` before treating by-query
  task rethrottle state, repeated last-write-wins sequencing, and readback as
  runtime-control evidence, including shared-runtime restart readback for
  requested throttle rates, cancelled/terminal task refusal, and same-node
  parent/child plus multi-level descendant independent rate readback, plus
  rethrottle-request handling during the per-request sync window after restart.
- `tools/run-native-closure-validation.py --batch runtime-task-metadata` must
  report `failed_count == 0` and `zero_test_count == 0` before treating parent
  task metadata and cat task readback as runtime-control evidence.
- `tools/run-native-closure-validation.py --batch runtime-task-headers` must
  report `failed_count == 0` and `zero_test_count == 0` before treating task
  request-header readback as runtime-control evidence.
- `tools/run-native-closure-validation.py --batch runtime-task-children` must
  report `failed_count == 0` and `zero_test_count == 0` before treating
  same-node parent/child task grouping and parent-task-id child cancellation
  visibility, same-node and cross-node multi-level descendant cancellation
  propagation, background-worker descendant cancellation propagation, plus
  parent/child and multi-level descendant rethrottle rate visibility as
  runtime-control evidence.

### 3. Mixed-Cluster Movement Hardening

Goal: turn the existing representative shard movement proof into interruption
and retry evidence.

Already evidenced:

- Java primary to SteelSearch replica placement;
- SteelSearch primary promotion after Java primary loss;
- Java replica rejoin behind SteelSearch primary;
- Java primary recovery after SteelSearch node loss;
- zero observed shard checkpoint drift in the representative probe.

Remaining tests:

1. interrupt Java to SteelSearch recovery before finalize;
2. interrupt SteelSearch primary to Java replica recovery before finalize;
3. restart the recovering target and verify explicit resume or bounded restart;
4. verify retention-lease and checkpoint monotonicity during interruption;
5. capture allocation explanation for unsupported movement shapes.

Exit evidence:

- live probe artifacts include `interrupted`, `resumed_or_restarted`, and
  `finalized` phases for both directions;
- each phase records placement, visibility, recovery state, and checkpoint
  drift;
- unsupported cases fail closed with a ledger row.

### 4. Production Runtime Controls

Goal: move from development runtime substitutes to a Rust-native runtime
control model with OpenSearch-shaped API boundaries.

Initial targets:

1. bootstrap/preflight refusal tests for data-path, bind, role, and production
   mode settings. Guarded batch evidence now exists for this slice;
2. task registry model with cancellation and parent/child metadata. Runtime
   mutation evidence now exists for bounded cancellation/readback and by-query
   rethrottle/readback; parent task metadata, task header readback, same-node
   child grouping, same-node multi-level child cancellation propagation, and
   same-node parent/child plus multi-level rethrottle rate visibility now have
   guarded coverage;
3. queue/backpressure smoke tests for search/write/admin routes. Runtime queue
   depth evidence now exists for cluster-manager task visibility and
   administrative thread-pool telemetry, and search/write route completion
   counters are derived from runtime-owned thread-pool state for both success
   and request-error paths; active-slot queue waiting/drain, independent mixed
   search/maintenance backlog drain, and queue-full overload rejection are now
   guarded for search/write, maintenance, and snapshot pools, plus cluster
   reroute and task-submission admission, with
   accepted queued task-submission no-replay covered across shared-runtime
   restart and partial shared-state recovery errors, partial-recovery
   task-submission refusal and live-shutdown task-submission refusal covered,
   and with
   local overload counters and local search/write admission isolated from
   remote task metadata in multi-node task visibility;
4. telemetry rows that are derived from runtime state rather than static route
   stubs.

Exit evidence:

- startup refusal harness passes;
- task cancellation probe mutates real task state;
- telemetry and readiness outputs cite the same blocker categories.

### 5. Production Security

Goal: replace fail-closed production security blockers with enforced Rust-native
security boundaries or explicit fail-closed compatibility decisions.

Initial targets:

1. TLS bootstrap policy and certificate validation fixtures;
2. authentication subject model for users and service accounts;
3. role and index permission evaluator;
4. audit log entries for allowed and denied sensitive operations;
5. redaction tests for responses, logs, readiness, snapshots, and migration
   manifests.

Exit evidence:

- secure standalone harness passes authn/authz and redaction fixtures;
- production mode starts only when every required security boundary is
  `Enforced`;
- unsupported OpenSearch Security plugin APIs fail closed with documented
  errors.

## Immediate Execution Order

1. Add a reusable non-native path report.
2. Use that report to keep the source-backed and vector/hybrid inventories
   current.
3. Extend the live shard movement probe with interruption and resume phases.
4. Add startup/preflight refusal tests before broad runtime-control wiring.
5. Continue security from the structured fail-closed boundary/checklist gate
   into TLS/authn bootstrap fixtures, then add real enforcement paths.
