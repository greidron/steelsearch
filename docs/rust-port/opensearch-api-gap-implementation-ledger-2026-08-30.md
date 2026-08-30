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
| API-SNAPSHOT-RESTORE-REMOTE-OPTIONS-001 | Snapshot/restore | Restore requests that ask for remote-backed restore behavior (`source_remote_store_repository`, `source_remote_translog_repository`, `storage_type=remote_snapshot`) or experimental backing-index attachment (`attach_to_data_stream=true`) now fail closed instead of being silently accepted and ignored. `storage_type=local` and `attach_to_data_stream=false` remain accepted no-ops inside the existing local restore subset. | bounded | `crates/os-node/src/standalone_runtime.rs` | `snapshot_restore_fails_closed_for_unsupported_remote_backed_options`; `snapshot_restore` test filter | Targeted tests: `cargo fmt --check`; `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_restore_fails_closed_for_unsupported_remote_backed_options --features standalone-runtime -- --nocapture`; `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_restore --features standalone-runtime -- --nocapture`; `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node --lib --features standalone-runtime` reports 570 passed. Full benchmark `target/search-benchmark-matrix-api-restore-unsupported-options-full-20260830/summary.json`: SteelSearch single-node `717.78 ops/s` vs OpenSearch `219.55 ops/s`; SteelSearch three-node `866.41 ops/s` vs OpenSearch `81.21 ops/s`; no SteelSearch-slower-than-OpenSearch metrics. | Full remote-backed restore and `attach_to_data_stream=true` are not implemented. This row prevents replacement cutover automation from receiving a false success for unsupported restore semantics. |
| API-SNAPSHOT-DS-RENAME-001 | Snapshot/restore + data streams | Restore by data stream name with `rename_pattern`/`rename_replacement` now rewrites restored backing-index names and data stream metadata to the renamed data stream, preserving search visibility through the renamed data stream. | closed | `crates/os-node/src/standalone_runtime.rs` | `snapshot_restore_rehydrates_data_stream_metadata_and_backing_index`; `tools/fixtures/snapshot-lifecycle-compat.json`; `tools/snapshot_lifecycle_compat.py` | Targeted/live gates: `cargo fmt --check`; `python3 -m json.tool tools/fixtures/snapshot-lifecycle-compat.json`; `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node --lib --features standalone-runtime` reports 570 passed; live compare `target/api-gap-snapshot-data-stream-rename-20260830/compare/snapshot-lifecycle-compat-report.json`: 50 passed, 0 failed, 0 skipped. Full benchmark `target/search-benchmark-matrix-api-snapshot-data-stream-rename-full-20260830/summary.json`: SteelSearch single-node `724.85 ops/s` vs OpenSearch `223.95 ops/s`; SteelSearch three-node `881.69 ops/s` vs OpenSearch `79.22 ops/s`; no SteelSearch-slower-than-OpenSearch metrics. | Internal data stream backing-index date/UUID formatting remains bounded; public replacement behavior is compared through restore acceptance, `_data_stream` readback name/backing count, and renamed data stream search total. |
| API-SNAPSHOT-RESTORE-FEATURE-STATES-001 | Snapshot/restore | Restore requests that explicitly ask for `feature_states` now fail closed instead of being accepted and ignored. | bounded | `crates/os-node/src/standalone_runtime.rs` | `snapshot_restore_fails_closed_for_unsupported_remote_backed_options`; `snapshot_restore` test filter | Targeted/full gates: `cargo fmt --check`; `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_restore_fails_closed_for_unsupported_remote_backed_options --features standalone-runtime -- --nocapture`; `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_restore --features standalone-runtime -- --nocapture`; `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node --lib --features standalone-runtime` reports 570 passed; `RUSTFLAGS='-Awarnings' cargo +nightly build -q --release -p os-node --bin steelsearch --features standalone-runtime`; full benchmark `target/search-benchmark-matrix-api-feature-states-fail-closed-full-20260830/summary.json`: SteelSearch single-node `731.12 ops/s` vs OpenSearch `213.64 ops/s`; SteelSearch three-node `883.39 ops/s` vs OpenSearch `83.30 ops/s`; no SteelSearch-slower-than-OpenSearch metrics. | Full feature-state restore is not implemented. This row prevents restore automation from receiving a false success for cluster feature state recovery outside SteelSearch's bounded snapshot restore subset. |
| API-SNAPSHOT-CREATE-SELECTORS-001 | Snapshot/create | Snapshot creation now resolves OpenSearch-style `indices` selectors before capture, including wildcard selectors and negative exclusions across index and data stream names. Missing positive selectors return `404 index_not_found_exception` unless `ignore_unavailable=true`; `partial=true` does not mask missing selectors. | closed | `crates/os-node/src/standalone_runtime.rs` | `snapshot_create_resolves_selectors_and_uses_ignore_unavailable_not_partial`; `tools/fixtures/snapshot-lifecycle-compat.json`; `tools/snapshot_lifecycle_compat.py` | Targeted/live gates: `cargo fmt --check`; `python3 -m json.tool tools/fixtures/snapshot-lifecycle-compat.json`; `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_create_resolves_selectors_and_uses_ignore_unavailable_not_partial --features standalone-runtime -- --nocapture`; `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_restore --features standalone-runtime -- --nocapture`; `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node --lib --features standalone-runtime` reports 571 passed; focused live compare `target/api-gap-snapshot-create-selectors-20260830/snapshot-create-selectors-focused-report.json`: 3 passed, 0 failed, 0 skipped. Full benchmark `target/search-benchmark-matrix-api-snapshot-create-selectors-full-20260830/summary.json`: SteelSearch single-node `736.88 ops/s` vs OpenSearch `212.98 ops/s`; SteelSearch three-node `877.10 ops/s` vs OpenSearch `83.35 ops/s`; no SteelSearch-slower-than-OpenSearch metrics. | Deeper shard-level partial failure materialization remains bounded; this row closes selector resolution and missing-selector API parity for replacement workflows. |

## Open Items

| Priority | Area | Remaining gap | Why it matters | Next evidence |
|---|---|---|---|---|
| P1 | Snapshot/restore | Broader restore option combinations: partial shard failure materialization. | Cutover automation can depend on exact failure semantics. | Add rows to `tools/fixtures/snapshot-lifecycle-compat.json` and compare against live OpenSearch. |
| P1 | Snapshot/restore | Remote-backed restore options and restored backing-index attachment are fail-closed, not implemented. | Remote-store cutover workflows need explicit unsupported responses rather than false success. | Add live compare rows once an OpenSearch remote-backed fixture is available. |
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
- The remote-backed restore option fail-closed row is outside the steady-state
  search benchmark hot path. Its full matrix reported SteelSearch single-node
  717.78 ops/s and three-node 866.41 ops/s, with no
  SteelSearch-slower-than-OpenSearch metrics.
- The feature-state restore fail-closed row is outside the steady-state search
  benchmark hot path. Its full matrix reported SteelSearch single-node
  731.12 ops/s and three-node 883.39 ops/s, with no
  SteelSearch-slower-than-OpenSearch metrics. Compared with the preceding
  no-op refresh full baseline, SteelSearch throughput moved by -0.95%
  single-node and -0.37% three-node, while refresh p99 improved by 3.77% and
  9.52% respectively.
- The snapshot-create selector row is outside the steady-state search
  benchmark hot path. Its full matrix reported SteelSearch single-node
  736.88 ops/s and three-node 877.10 ops/s, with no
  SteelSearch-slower-than-OpenSearch metrics. Compared with the preceding
  feature-state fail-closed full baseline, SteelSearch throughput moved by
  +0.79% single-node and -0.71% three-node; refresh p99 moved by -6.59%
  single-node and +1.64% three-node, so the API change is classified as
  performance-neutral.
- The data-stream rename restore row is outside the steady-state search
  benchmark hot path. Its full matrix reported SteelSearch single-node
  724.85 ops/s and three-node 881.69 ops/s, with no
  SteelSearch-slower-than-OpenSearch metrics.
