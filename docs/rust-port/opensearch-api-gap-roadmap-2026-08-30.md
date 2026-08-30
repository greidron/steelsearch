# OpenSearch API Gap Roadmap

Date: 2026-08-30

Scope: API-level compatibility needed for replacing an OpenSearch cluster with
SteelSearch, or using SteelSearch with OpenSearch in a bounded mixed mode.
Index-file-level and Lucene-directory compatibility are intentionally outside
this scope.

## Current Evidence

- Required live OpenSearch E2E profile: no remaining failed or missing cases in
  `docs/rust-port/opensearch-e2e-gap-inventory.md`.
- Source-derived REST route ledger: no missing safe read/head routes in
  `docs/api-spec/generated/runtime-route-ledger.md`.
- Mixed-cluster representative evidence: `target/mixed-cluster-coverage-current.json`
  reports `passed=true`.
- v0.5.0 final performance evidence:
  `target/search-benchmark-matrix-v050-final-full-20260830/summary.json`.

This is enough to say the current required comparison profile is green. It is
not enough to claim exhaustive OpenSearch API compatibility.

## Replacement-Relevant API Gaps

| Priority | Area | Gap | Impact | Status |
|---|---|---|---|---|
| P0 | Field capabilities | `include_unmapped=true` only had parameter validation and did not emit `unmapped` type entries. | Schema-discovery clients can misread mixed-index field availability. | Fixed in this pass. |
| P0 | Field capabilities | `include_unmapped=true` mapped field type entries did not expose the mapped index list when OpenSearch emits `indices`. | Clients that inspect per-index field availability could see less detail than OpenSearch. | Fixed in this pass. |
| P0 | Search/metadata evidence | `/_field_caps` routes were implemented but still classified with no canonical evidence owner in generated API docs. | Gap inventory understated existing canonical compare coverage. | Fixed in this pass. |
| P1 | Snapshot/restore | Restore-time `index_settings` and `ignore_index_settings` were not applied to restored index metadata. | Cutover workflows that adjust settings during restore could produce materially different restored indices. | Fixed in this pass. |
| P1 | Snapshot/restore | Snapshot lifecycle and restore support are still bounded beyond the covered option combinations. | Migration/cutover workflows must stay inside documented restore subset. | Still bounded. |
| P1 | Snapshot/restore | Remote-backed restore options (`source_remote_store_repository`, `source_remote_translog_repository`, `storage_type=remote_snapshot`) and `attach_to_data_stream=true` were silently accepted but not implemented. | Remote-store cutover workflows could misread unsupported restore semantics as success. | Fixed as bounded fail-closed behavior in follow-up pass; tracked as `API-SNAPSHOT-RESTORE-REMOTE-OPTIONS-001`. |
| P1 | Snapshot/restore | Restore `indices` selection treated `partial=true` as missing-index tolerance and only handled exact names. | Cutover restore requests using OpenSearch multi-index syntax or `ignore_unavailable` could restore the wrong set or silently diverge. | Fixed in follow-up pass. |
| P1 | Snapshot/restore | Restore accepted `rename_alias_pattern` and `rename_alias_replacement` but did not apply them to restored aliases. | Alias-based cutover/read-write clients could point at different alias names after restore. | Fixed in follow-up pass. |
| P1 | Snapshot/restore | Restore target collision against an existing open index returned `409 resource_already_exists_exception` instead of OpenSearch's `500 snapshot_restore_exception`. | Cutover automation that branches on OpenSearch restore failure type/status could misclassify restore safety failures. | Fixed in follow-up pass. |
| P1 | Snapshot/restore + data streams | Snapshot creation by data stream name did not fully materialize backing shard snapshot state for restore, and restore did not reattach data stream metadata. | Data-stream based cutover could restore backing index state without a usable data stream API target. | Fixed in follow-up pass; tracked as `API-SNAPSHOT-DS-RESTORE-001` in the implementation ledger. |
| P1 | Snapshot/restore + data streams | Restore by data stream name with `rename_pattern`/`rename_replacement` did not rewrite restored backing-index names to the renamed data stream. | Data-stream based cutover could produce a renamed public data stream whose backing index metadata/search visibility diverged from OpenSearch. | Fixed in follow-up pass; tracked as `API-SNAPSHOT-DS-RENAME-001` in the implementation ledger. |
| P1 | Field capabilities | POST `/_field_caps` accepted `index_filter` bodies but did not apply them to the resolved index set. | Schema-discovery clients could see fields from indices OpenSearch would filter out. | Fixed in follow-up pass; term and range evidence now covered. |
| P1 | Field capabilities | Same field names with different mapped types across resolved indices were collapsed to the first observed type. | Schema-discovery clients could miss OpenSearch-style per-type field capability entries. | Fixed in follow-up pass. |
| P1 | Search semantic depth | Required suites pass, but full parameter-space depth is not exhaustive. | Advanced clients may hit untested edge combinations. | Expand by fixture families. |
| P1 | Mixed-cluster interop | Representative mixed-cluster evidence exists, but authoritative same-cluster peer-node membership is still not a broad production claim. | Unsafe membership/write-replication cases must fail closed. | Continue Phase C evidence expansion. |
| P2 | Flight/plugin example routes | `/_flight/stats`, `/_nodes/flight/stats`, `/_cat/example`, `/test/_stream`, and SteelSearch-only helper routes are out of source-required runtime compare scope. | Low replacement impact unless a specific plugin/client depends on them. | Defer unless demanded by client workload. |

## Implemented In This Pass

- `GET/POST /_field_caps` and `GET/POST /{index}/_field_caps` now have search
  evidence ownership in generated API docs.
- `/_field_caps?include_unmapped=true` now returns an `unmapped` field type for
  selected fields that are mapped in some resolved indices and absent in others.
- For the same mixed-index response, mapped field type entries now include the
  OpenSearch-style `indices` list for indices where the field is mapped.
- Search compatibility fixture now includes
  `field_caps_include_unmapped_summary`, compared against live OpenSearch.
- Snapshot restore now applies OpenSearch-style restore-time `index_settings`
  overrides and `ignore_index_settings` filtering to restored index metadata.
- Snapshot lifecycle fixture now compares restored `number_of_replicas`,
  `refresh_interval`, and ignored `priority` settings against live OpenSearch.
- POST `/_field_caps` and `/{index}/_field_caps` now apply `index_filter` to
  the resolved index set before field type and `include_unmapped` calculation.
- Search compatibility fixture now includes
  `field_caps_index_filter_term_summary`, compared against live OpenSearch.
- `/_field_caps` now preserves multiple mapped types for the same field across
  resolved indices and emits per-type `indices` lists when OpenSearch does.
- Search compatibility fixture now includes
  `field_caps_mixed_type_summary`, compared against live OpenSearch.
- Search compatibility fixture now also includes
  `field_caps_index_filter_range_summary`, proving the existing
  `index_filter` support beyond the original term-only evidence row.
- Snapshot restore now resolves OpenSearch-style `indices` multi-index syntax
  inside the snapshot, including wildcard selectors, negative exclusions, and
  `ignore_unavailable=true` for missing selectors.
- Restore `partial=true` no longer masks missing index selectors; missing index
  tolerance is controlled by `ignore_unavailable`, matching OpenSearch behavior.
- Snapshot restore now preflights rename target collisions before materializing
  restored index metadata or documents.
- Snapshot restore now applies `rename_alias_pattern` and
  `rename_alias_replacement` to restored alias metadata when aliases are
  included.
- Snapshot restore target collisions against an existing open index now return
  OpenSearch-compatible `500 snapshot_restore_exception` responses, and the
  live snapshot lifecycle fixture pins that behavior.
- Snapshot create by data stream name now captures backing index metadata and
  documents, records the OpenSearch-style `data_streams` list, persists restore
  shard manifests for backing indices, and restore by data stream name now
  reattaches data stream metadata and makes the restored stream searchable.
- API gap implementation details are now tracked in
  `docs/rust-port/opensearch-api-gap-implementation-ledger-2026-08-30.md`.
- Snapshot restore now fails closed for unsupported remote-backed restore and
  experimental backing-index attachment options instead of accepting and
  ignoring them.

## Validation

- Targeted runtime test:
  `cargo +nightly test -q -p os-node field_caps_and_list_routes_serve_root_and_targeted_misc_shapes --features standalone-runtime`
- Live SteelSearch/OpenSearch compare:
  `target/search-compat-field-caps-include-unmapped-compare-indices.json`
- Benchmark after feature change:
  - `target/search-benchmark-matrix-api-fieldcaps-final-full-20260830/summary.json`
  - `target/search-benchmark-matrix-api-fieldcaps-final-full-repeat-20260830/summary.json`
- Snapshot/restore setting validation:
  `target/phase-a-acceptance-harness/local/compare/snapshot-lifecycle-compat-report.json`
  reports `28 passed, 0 failed, 0 skipped`.
- Benchmark after snapshot/restore setting change:
  `target/search-benchmark-matrix-api-snapshot-restore-settings-full-20260830/summary.json`
- Final HEAD benchmark and report:
  - `target/search-benchmark-matrix-final-head-full-20260830/summary.json`
  - `target/search-benchmark-matrix-final-head-full-20260830/report.md`
  - `docs/rust-port/final-benchmark-report-2026-08-30.md`
- Development replacement gate:
  `tools/run-development-replacement-gate.sh` passed with exit code 0.
- Follow-up `index_filter` validation:
  - Targeted runtime test:
    `cargo +nightly test -q -p os-node field_caps_and_list_routes_serve_root_and_targeted_misc_shapes --features standalone-runtime`
  - Live SteelSearch/OpenSearch compare:
    `target/search-compat-field-caps-index-filter.json`
  - Development replacement gate:
    `tools/run-development-replacement-gate.sh` passed with exit code 0.
  - Full benchmark:
    `target/search-benchmark-matrix-api-fieldcaps-index-filter-full-20260830/summary.json`
  - Single-node repeat:
    `target/search-benchmark-matrix-api-fieldcaps-index-filter-steel-single-rerun-20260830/summary.json`
- Follow-up mixed field-type validation:
  - Targeted runtime test:
    `cargo +nightly test -q -p os-node field_caps_and_list_routes_serve_root_and_targeted_misc_shapes --features standalone-runtime`
  - Live SteelSearch/OpenSearch compare:
    `target/search-compat-field-caps-mixed-type.json`
  - Development replacement gate completed; daemon-backed search compatibility
    reports `1097 passed, 0 failed, 0 skipped`.
  - Full benchmark:
    `target/search-benchmark-matrix-api-fieldcaps-mixed-type-full-20260830/summary.json`
- Follow-up field caps range `index_filter` validation:
  - Targeted runtime test:
    `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node field_caps_and_list_routes_serve_root_and_targeted_misc_shapes --features standalone-runtime`
  - Live SteelSearch/OpenSearch compare:
    `target/api-gap-fieldcaps-range-filter-20260830/search-compat-report.json`
    reports `1 passed, 0 failed, 0 skipped` for the new range filter row.
  - No runtime code changed in this pass; the preceding snapshot restore
    conflict runtime change is covered by the full matrix at
    `target/search-benchmark-matrix-api-snapshot-restore-conflict-full-20260830/summary.json`.
- Follow-up snapshot restore selector validation:
  - Targeted runtime test:
    `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_restore --features standalone-runtime`
  - Live SteelSearch/OpenSearch compare:
    `target/snapshot-restore-selector-compat-20260830-rerun/snapshot-lifecycle-compat-report.json`
    reports `21 passed, 0 failed, 0 skipped`.
  - Full benchmark:
    `target/search-benchmark-matrix-api-snapshot-restore-selectors-full-20260830/summary.json`
- Follow-up snapshot restore alias rename validation:
  - Targeted runtime tests:
    `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_restore --features standalone-runtime`
    and
    `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_restore_body_subset_keeps_bounded_fields_only --features standalone-runtime`
  - Live SteelSearch/OpenSearch compare:
    `target/snapshot-restore-alias-rename-compat-20260830/snapshot-lifecycle-compat-report.json`
    reports `25 passed, 0 failed, 0 skipped`.
  - Full benchmark:
    `target/search-benchmark-matrix-api-snapshot-restore-alias-rename-full-20260830/summary.json`
  - Single-node repeat:
    `target/search-benchmark-matrix-api-snapshot-restore-alias-rename-steel-single-rerun-20260830/summary.json`
- Follow-up snapshot restore existing-index conflict validation:
  - Targeted runtime test:
    `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_repository_type_validation_and_restore_preconditions_fail_closed --features standalone-runtime`
  - Live SteelSearch/OpenSearch compare:
    `target/api-gap-snapshot-restore-conflict-fixed-20260830/snapshot-lifecycle-compat-report.json`
    reports `28 passed, 0 failed, 0 skipped`; the conflict row compares
    `500 snapshot_restore_exception` on both targets.
  - Full benchmark:
    `target/search-benchmark-matrix-api-snapshot-restore-conflict-full-20260830/summary.json`
    reports single-node `636.407 ops/s` vs OpenSearch `206.133 ops/s`
    (`3.087x`) and three-node `795.274 ops/s` vs OpenSearch `70.522 ops/s`
    (`11.277x`), with no SteelSearch-slower-than-OpenSearch metrics.
- Follow-up snapshot data stream restore validation:
  - Targeted runtime tests:
    `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_restore --features standalone-runtime`
    and
    `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node data_stream --features standalone-runtime`
  - Full lib test:
    `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node --lib --features standalone-runtime`
    reports `569 passed, 0 failed`.
  - Live SteelSearch/OpenSearch compare:
    `target/api-gap-snapshot-data-stream-restore-20260830-final/snapshot-lifecycle-compat-report.json`
    reports `34 passed, 0 failed, 0 skipped`.
  - Development replacement gate:
    `target/development-replacement-gate-api-snapshot-data-stream-20260830-rerun.log`
    completed with exit code 0 before the final no-op warning cleanup; the
    post-cleanup lib and snapshot tests passed.
  - Full benchmark:
    `target/search-benchmark-matrix-api-snapshot-data-stream-full-20260830/summary.json`
    reports single-node `654.37 ops/s` vs OpenSearch `201.95 ops/s`
    (`3.24x`) and three-node `812.14 ops/s` vs OpenSearch `79.30 ops/s`
    (`10.24x`), with no SteelSearch-slower-than-OpenSearch metrics.
  - Single-node repeat:
    `target/search-benchmark-matrix-api-snapshot-data-stream-steel-single-rerun-20260830/summary.json`
    reports `664.50 ops/s` and refresh p99 `23.07 ms`, classifying the
    full-run refresh p99 spike as non-persistent benchmark noise.
- Follow-up snapshot data stream rename restore validation:
  - Full lib test:
    `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node --lib --features standalone-runtime`
    reports `570 passed, 0 failed`.
  - Live SteelSearch/OpenSearch compare:
    `target/api-gap-snapshot-data-stream-rename-20260830/compare/snapshot-lifecycle-compat-report.json`
    reports `50 passed, 0 failed, 0 skipped`.
  - Full benchmark:
    `target/search-benchmark-matrix-api-snapshot-data-stream-rename-full-20260830/summary.json`
    reports single-node `724.85 ops/s` vs OpenSearch `223.95 ops/s`
    (`3.24x`) and three-node `881.69 ops/s` vs OpenSearch `79.22 ops/s`
    (`11.13x`), with no SteelSearch-slower-than-OpenSearch metrics.
- Follow-up snapshot remote-backed option validation:
  - Targeted runtime tests:
    `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_restore_fails_closed_for_unsupported_remote_backed_options --features standalone-runtime -- --nocapture`
    and
    `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_restore --features standalone-runtime -- --nocapture`
  - Full lib test:
    `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node --lib --features standalone-runtime`
    reports `570 passed, 0 failed`.
  - Full benchmark:
    `target/search-benchmark-matrix-api-restore-unsupported-options-full-20260830/summary.json`
    reports single-node `717.78 ops/s` vs OpenSearch `219.55 ops/s`
    (`3.27x`) and three-node `866.41 ops/s` vs OpenSearch `81.21 ops/s`
    (`10.67x`), with no SteelSearch-slower-than-OpenSearch metrics.

Latest repeats after the change:

| Topology | Throughput |
|---|---:|
| single-node | 646.592 ops/s |
| three-node | 810.837 ops/s |
| single-node repeat | 641.137 ops/s |
| three-node repeat | 815.519 ops/s |

These are below the v0.5.0 final SteelSearch run
(`651.653 ops/s` single-node, `827.631 ops/s` three-node), but the modified code
is limited to `/_field_caps` response construction and the Python compatibility
extractor; the benchmark workload does not call this API. The latest repeats
still remain ahead of the v0.5.0 OpenSearch comparison baseline
(`197.384 ops/s` single-node, `70.808 ops/s` three-node).

After the snapshot/restore setting change, the full SteelSearch benchmark
reported:

| Topology | Throughput | Refresh p99 |
|---|---:|---:|
| single-node | 647.482 ops/s | 25.888 ms |
| three-node | 837.379 ops/s | 34.184 ms |

The snapshot/restore code is outside the search benchmark hot path. The
three-node run is above the v0.5.0 final SteelSearch baseline, and the
single-node run remains within the same post-v0.5.0 measurement band while
staying over 3.2x the v0.5.0 OpenSearch single-node baseline.

The final HEAD full matrix reported:

| Topology | SteelSearch Throughput | OpenSearch Throughput | Ratio | Refresh p99 |
|---|---:|---:|---:|---:|
| single-node | 651.052 ops/s | 205.104 ops/s | 3.17x | 22.266 ms |
| three-node | 825.115 ops/s | 85.286 ops/s | 9.68x | 33.333 ms |

The benchmark reported no SteelSearch-slower-than-OpenSearch metrics for either
topology.

The mixed field-type follow-up full matrix reported:

| Topology | SteelSearch Throughput | OpenSearch Throughput | Ratio | Refresh p99 |
|---|---:|---:|---:|---:|
| single-node | 633.005 ops/s | 208.806 ops/s | 3.03x | 24.072 ms |
| three-node | 826.675 ops/s | 76.944 ops/s | 10.74x | 28.182 ms |

The benchmark again reported no SteelSearch-slower-than-OpenSearch metrics. The
single-node throughput is lower than the immediately preceding full matrix, but
the changed code is limited to `/_field_caps` response construction and fixture
coverage; the benchmark workload does not call this API. Three-node throughput
is neutral to slightly positive versus the preceding full matrix.

## Next Implementation Order

1. Snapshot/restore option-depth: feature states and partial shard restore
   compare rows.
2. Field caps deeper parity: additional `index_filter` query-shape fixtures
   beyond the currently covered term case.
3. Search parameter edge families: less common combinations that are currently
   covered by representative rather than exhaustive tests.
4. Mixed-cluster Phase C: extend failure-path evidence around membership,
   publication, recovery, and write-replication fail-closed behavior.
