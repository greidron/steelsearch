# Core Replacement Exclusion Ledger

Scope: the implementation plan dated 2026-09-07; plugins remain out of scope.
This ledger records rejected implementations, not successful completion of
the affected functional requirement.

## Admission Rule

The user authorized exclusion of a single implementation that causes at least
5% degradation and cannot be corrected by optimization. Establish the change's
incremental impact against the immediate prior implementation with matching
workloads and verified binaries. Separately retain its cumulative comparison
against the immutable v0.6.0 baseline. A cumulative failure alone does not prove
that one individual change caused at least 5% degradation.

Reproduce the impact using the predefined full benchmark/repetition procedure,
profile the affected path, and record feasible correctness-preserving optimization
attempts and their results. Do not declare optimization impossible from one
unfavorable run. Do not alter functionality, durability or security to obtain a
passing measurement. Exclude only the attributable implementation; preserve
unrelated work and explicitly mark its functional requirement as unresolved.

After exclusion, rerun the full suite on the retained candidate. An exclusion
must not shift the initial baseline, hide a regression in another metric, or
silently enable an unsupported feature. If rejecting a change would leave an
existing supported path unsafe, keep that deployment profile blocked instead
of treating the unsafe behavior as a completed replacement.

## Required Entry

Each entry must contain:

- Unique exclusion ID and the plan's implementation ID.
- Feature, intended behavior and affected deployment profiles.
- Source commits and actual v0.6.0/prior/candidate executable hashes.
- Full raw benchmark paths and hashes, actual settings, execution order and dates.
- Incremental and cumulative throughput/mean/p95/p99 differences by affected row.
- Reproduction and CPU/allocation/IO evidence identifying the cost.
- Optimization alternatives tried, correctness checks and measured outcomes.
- Exact excluded code/feature boundary, retained source/binary identity.
- Post-exclusion full benchmark and functional test results.
- Remaining unsupported requirement and conditions for revisiting the exclusion.

## Entries

| ID | Plan ID | Feature | Incremental impact | v0.6.0 cumulative impact | Evidence | Disposition |
| --- | --- | --- | --- | --- | --- | --- |
| EXC-20260913-01 | PERF-ACTIX-DIRECT-HANDLER-20260913 | Remove the REST `web::block` boundary | Single-node write p99 +216.1% to +221.0% | No cumulative improvement; retained candidate remains outside the gate | r61/r63/r64 below | Rejected and removed from candidate |

### EXC-20260913-01: Direct Actix REST Handler

- **Intended behavior and affected profiles:** execute the synchronous REST
  request handler directly on an Actix worker instead of submitting it through
  `web::block`. This was a runtime performance experiment, not a functional
  replacement-plan capability. It affects every standalone REST deployment,
  with the single-node latency profile materially affected.
- **Source and executable identities:** the worktree parent was
  `cbb5866ed32771ca326ebd004569c4c884929ca`; the benchmark source is an
  isolated, uncommitted candidate copy at
  `target/core-replacement-c06/native-termvectors-source`. The retained
  executable is `0e7e90e3c96d2ed967e6b5a5462dc69ae833e5cd8861449fc6950c5c08ad9c6e`.
  The direct-handler trial executable is
  `faa89528fbfcad4ca5ced5623b32aa788957840de93decbdf9ed1897d3b66753`.
  The fixed published v0.6.0 evidence is
  `docs/releases/v0.6.0/current.json`
  (`d2fdabfa447830f91b320aaebd734e01606deb70219e71b53d10c9281538c788`).
- **Reproduction and raw evidence:** all runs used the recorded non-plugin
  workload: 60 seconds, four clients, 5,000 documents, three shards,
  write/lexical/ranking/facet/sort_filter/nested/refresh =
  15/15/15/15/10/10/5, seed 13, `minilm-knn`, development durability,
  native writes and the recorded security/resource settings. Execution order
  was baseline, candidate, OpenSearch, OpenSearch, candidate, baseline.
  - Prior retained candidate, 2026-09-13:
    `target/core-replacement-c06/restored-native-aggregation-parallel-repeated-full-r61-20260913/result.json`
    (`a64949d40f2a1a837ec335aa25ba2af52e9717f291428195716260c539ad744f`).
  - Direct-handler trial, 2026-09-13:
    `target/core-replacement-c06/direct-actix-handler-repeated-full-r63-20260913/result.json`
    (`1262d2f7c460753729ad4a8b65f8d63692583bcccd63ce8d879d3d064e3a42b3`).
  - Post-exclusion retained candidate, 2026-09-13:
    `target/core-replacement-c06/actix-direct-handler-exclusion-restored-r64-20260913/result.json`
    (`347f7c5e86d712457551e2e83f47d445992eaad0c70f8b9c17f6a7d6b61b367c`);
    its plan hash is
    `5ebbb52a896ae69c80b6febc687eecf12f42a32d23a75e085bba93c95300d4bf`.
- **Incremental impact:** matched r61 to r63 candidate repetitions show that
  the direct handler changed single-node throughput by +0.79% and +1.25%, but
  increased write p99 by +221.0% and +216.1%, lexical p99 by +82.6% and
  +91.2%, nested p99 by +66.0% and +67.2%, and refresh p99 by +44.3% and
  +35.8%. The first/second three-node measurements did not reproduce that tail
  cost, which confines the rejection to the harmed single-node profile rather
  than claiming a general throughput regression. The direct change improved
  single-node `sort_filter` p99 by 10.3% and 11.9%, but that improvement does
  not offset independent latency gate failures and does not identify the
  sort/filter root cause.
- **Cumulative evidence:** r63 still failed the fixed v0.6.0 comparison. Its
  single-node sort/filter mean/p95/p99 were 13.02/36.60/47.28 ms against
  4.57/9.30/14.15 ms in the paired baseline; the retained r64 candidate was
  likewise outside the cumulative gate. r64 is a successful execution-verified
  post-exclusion run, not an acceptance result: its two published checks had
  22 and 26 failed values, and its paired checks had 16 and 16 failed values.
- **Diagnostic evidence:** the retained-binary sort/filter CPU diagnostic is
  `target/core-replacement-c06/r61-single-sort-filter-cpu/diagnostic.json`
  with `perf.data`; the matching futex diagnostic is
  `target/core-replacement-c06/r61-single-sort-filter-futex/diagnostic.json`
  with `perf.data`. The samples showed significant REST blocking-pool
  submission/wait activity and response serialization/allocation, while native
  multi-sort collection itself was present but not the dominant sampled CPU
  cost. They justified trying the boundary removal but do not prove that it is
  a safe optimization.
- **Alternatives and checks:** the direct handler was the minimal no-offload
  formulation. Its exact REST runtime tests passed before the full trial:
  TLS root-route serving and search/bulk runtime-thread-pool accounting. No
  correctness-preserving adjustment to that formulation removes the observed
  worker tail without restoring an offload boundary; restoring such a boundary
  is a different implementation. The candidate was restored exactly to the
  prior `web::block(move || encode_rest_response(node.handle_rest_request(...)))`
  path and rebuilt to the retained executable hash above.
- **Excluded boundary and remaining requirement:** only the direct execution
  of synchronous REST work on the Actix worker is excluded. No API or search
  functionality is marked complete or unsupported by this entry. Native
  sort/filter latency remains unresolved; any future runtime scheduling design
  must preserve the retained boundary's correctness and pass the full repeated
  non-plugin gate against the fixed v0.6.0 baseline before reconsideration.

Empty entries mean no qualifying exclusion has been established, not that all
planned functionality has been implemented or performance-validated.
