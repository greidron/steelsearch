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
   mode settings;
2. task registry model with cancellation and parent/child metadata;
3. queue/backpressure smoke tests for search/write/admin routes;
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
5. Start security with fail-closed TLS/authn bootstrap fixtures, then add real
   enforcement paths.
