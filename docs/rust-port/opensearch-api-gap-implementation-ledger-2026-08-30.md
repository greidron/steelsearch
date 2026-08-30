# OpenSearch API Gap Implementation Ledger

Date: 2026-08-30

Scope: API-level replacement compatibility for using SteelSearch instead of an
OpenSearch cluster, or in bounded mixed use with OpenSearch. Lucene directory
and index-file compatibility are out of scope.

## Ledger Rules

- Every row must name the API behavior, owning fixture/test, code surface, and
  benchmark evidence after the change.
- A row is `closed` only when live SteelSearch/OpenSearch comparison or an
  equivalent source-derived gate proves the behavior.
- A row remains `bounded` when the implemented API is usable for the documented
  replacement path but not exhaustive across OpenSearch's full option space.

## Current Route Coverage Baseline

- Source-derived REST coverage:
  `python3 tools/report-rest-api-coverage.py --summary-only` reports 379/379
  in-scope routes covered; 10 source routes are intentionally out of
  replacement scope.
- Runtime stateful probe:
  `docs/api-spec/generated/runtime-stateful-route-probe-report.json` reports no
  `semantic_coverage_missing` routes.
- Current broad compatibility profile before this ledger row:
  `target/development-replacement-gate-final-20260830.log` completed with exit
  code 0 and search compatibility reported 1098 passed, 0 failed, 0 skipped.

## Implementation Rows

| ID | Area | API behavior | Status | Code refs | Fixture/test refs | Evidence | Residual risk |
|---|---|---|---|---|---|---|---|
| API-SNAPSHOT-DS-RESTORE-001 | Snapshot/restore + data streams | Snapshot creation by data stream name captures backing index state/documents and records `data_streams`; restore by data stream name rehydrates data stream metadata, backing index metadata, and searchable documents. | closed | `crates/os-node/src/standalone_runtime.rs`, `crates/os-node/src/snapshot_lifecycle_route_registration.rs` | `snapshot_restore_rehydrates_data_stream_metadata_and_backing_index`; `tools/fixtures/snapshot-lifecycle-compat.json`; `tools/snapshot_lifecycle_compat.py` | Live compare `target/api-gap-snapshot-data-stream-restore-20260830-final/snapshot-lifecycle-compat-report.json`: 34 passed, 0 failed, 0 skipped. Full benchmark `target/search-benchmark-matrix-api-snapshot-data-stream-full-20260830/summary.json`; single-node repeat `target/search-benchmark-matrix-api-snapshot-data-stream-steel-single-rerun-20260830/summary.json`. | Data stream restore rename/date-naming parity is still bounded; live fixture intentionally compares data stream name and backing count rather than internal backing index date format. |

## Open Items

| Priority | Area | Remaining gap | Why it matters | Next evidence |
|---|---|---|---|---|
| P1 | Snapshot/restore | Broader restore option combinations: feature states, partial shard failure materialization, data stream rename edge cases. | Cutover automation can depend on exact failure and rename semantics. | Add rows to `tools/fixtures/snapshot-lifecycle-compat.json` and compare against live OpenSearch. |
| P1 | Search semantic depth | Required suites pass, but full parameter-space depth is not exhaustive. | Advanced clients can combine options outside current fixture coverage. | Expand search fixture families by client-observed workloads first. |
| P1 | Mixed-cluster interop | Representative evidence exists, but same-cluster peer-node membership and write-replication are still bounded claims. | Replacement/mixed deployment needs fail-closed behavior outside green-path probes. | Continue Phase C transport/admin fixtures and mixed-cluster gates. |
| P2 | Plugin/example routes | Flight stats, example routes, dashboard proxy, and test stream routes remain out of source-required runtime compare scope. | Low replacement impact unless a specific plugin/client depends on them. | Promote only if a real client workload requires them. |

## Performance Notes

- The snapshot/data-stream implementation is outside the steady-state search
  benchmark hot path.
- Full benchmark after the change: SteelSearch single-node 654.37 ops/s vs
  OpenSearch 201.95 ops/s; SteelSearch three-node 812.14 ops/s vs OpenSearch
  79.30 ops/s.
- The full run had one single-node refresh p99 tail spike at 45.27 ms. A
  same-profile SteelSearch single-node repeat reported 664.50 ops/s and refresh
  p99 23.07 ms, so this is classified as benchmark tail noise rather than a
  persistent regression from the API change.
