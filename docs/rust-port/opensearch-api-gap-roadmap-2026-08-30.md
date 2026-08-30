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
| P1 | Snapshot/restore | Snapshot lifecycle and restore support are bounded; full option-combination semantics are not proven. | Migration/cutover workflows must stay inside documented restore subset. | Still bounded. |
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

## Validation

- Targeted runtime test:
  `cargo +nightly test -q -p os-node field_caps_and_list_routes_serve_root_and_targeted_misc_shapes --features standalone-runtime`
- Live SteelSearch/OpenSearch compare:
  `target/search-compat-field-caps-include-unmapped-compare-indices.json`
- Benchmark after feature change:
  - `target/search-benchmark-matrix-api-fieldcaps-final-full-20260830/summary.json`
  - `target/search-benchmark-matrix-api-fieldcaps-final-full-repeat-20260830/summary.json`

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

## Next Implementation Order

1. Snapshot/restore option-depth: conflict handling, rename patterns, partial
   restore, and multi-index restore compare rows.
2. Field caps deeper parity: `index_filter` and mixed field-type reporting.
3. Search parameter edge families: less common combinations that are currently
   covered by representative rather than exhaustive tests.
4. Mixed-cluster Phase C: extend failure-path evidence around membership,
   publication, recovery, and write-replication fail-closed behavior.
