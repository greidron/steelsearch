# OpenSearch E2E Gap Inventory

This inventory covers the remaining live OpenSearch comparison failures after
the fixture cleanup, composable-template create-index support, search semantics
gap pass, index-visibility/count/stats pass, cluster-state shape pass,
significant-terms pass, multi-node write-path OpenSearch baseline pass, and ML
serving comparison pass.

Latest report:
`target/unified-opensearch-e2e-broad-current/unified-opensearch-e2e-report.json`

Latest audit report:
`target/unified-opensearch-e2e-audit/unified-opensearch-e2e-report.json`

Latest focused ML report:
`target/unified-opensearch-e2e-ml-focused-current/unified-opensearch-e2e-report.json`

Latest focused admin-ops report:
`target/unified-opensearch-e2e-admin-ops-current/unified-opensearch-e2e-report.json`

## Summary

- Total remaining failed rows: 0.
- Unique remaining case names: 0.
- Repeated in both `search-compat` and `search-strict`: 0 cases.
- Strict-only: none.
- Basic-only: none.
- `search-compat`: 1054 passed, 0 failed, 7 skipped.
- `search-strict`: 884 passed, 0 failed, 4 skipped.
- `search-semantic`: 75 passed, 0 failed, 0 skipped.
- `runtime-stateful-probe`: 519 passed, 0 failed, 0 skipped; 519 cases now
  carry case-level OpenSearch route-presence comparison evidence.
- `vector-search`: 25 passed, 0 failed, 0 skipped.
- `vector-search-native-surface`: 25 passed, 0 failed, 0 skipped.
- `knn-plugin-surface`: 8 passed, 0 failed, 0 skipped, all with live
  OpenSearch comparison evidence.
- `ml-model-surface`: 27 passed, 0 failed; all 27 cases have live OpenSearch
  comparison evidence. The fixture configures the OpenSearch ML Commons dev
  target for model deployment, waits for deploy task completion, uses a
  384-dimension neural index matching the OpenSearch text embedding model, and
  compares predict/neural serving route success without treating exact model
  embedding floats as stable parity keys.
- Focused `admin-ops-common`: 29 passed, 0 failed, 0 skipped, compared against
  live OpenSearch. This covers targeted close/search-closed,
  close/open/search-recovery, and closed-target `_refresh`, `_flush`,
  `_cache/clear`, and `_forcemerge` error parity, plus wildcard maintenance
  default-open and explicit `expand_wildcards=all` closed-index parity.
- `multi-node-transport-admin`: 15 passed, 0 failed, all with live OpenSearch
  comparison evidence, including remote REST PIT search/close forwarding
  through the transport path.
- Latest broad-current effective classification after the ML serving comparison
  refresh:
  `canonical_equal=2206`, `strict_equal=973`, `semantic_equal=3`,
  `steelsearch_fail_closed=0`, `steelsearch_only=0`,
  `known_gap_or_skipped=0`, `failed=0`, `missing=0`; the broad report status is
  `ok`.
- Latest focused ML report:
  `canonical_equal=27`, `failed=0`, `missing=0`, `steelsearch_only=0`;
  `predict_model`, `neural_query_search`, `neural_sparse_raw_search`, and
  `ml_model_lifecycle_shape` are canonical against live OpenSearch.
  `multi-node-transport-admin` now has live OpenSearch
  comparison evidence for all `15` cases. Security/authz has
  live OpenSearch comparison evidence for all `63` cases,
  `vector-search-native-surface` has live OpenSearch comparison evidence for
  all `25` cases, and `knn-plugin-surface` has live OpenSearch comparison
  evidence for all `8` cases. `multi-node-write-path` has live OpenSearch
  comparison evidence for all `9` cases while Steelsearch runs as a two-node
  topology.
- Effective required classification after skip resolution:
  `known_gap_or_skipped=0`; all 11 raw skipped cases are covered by other
  required suites.

## Remaining Gaps

No failed cases remain in the live `search-compat` plus `search-strict`
comparison profile.

## Exhaustive API Compatibility Audit

Current generated reports:

- `target/rest-api-coverage-current.json`
- `target/transport-action-coverage-current.json`
- `target/unified-opensearch-e2e-broad-current/unified-opensearch-e2e-report.json`

Current status:

| Area | Current evidence | Exhaustive-compatibility result |
| --- | --- | --- |
| Live required OpenSearch E2E suites | Latest broad-current effective summary is `failed=0`, `missing=0`, `known_gap_or_skipped=0` across `2206` canonical, `973` strict, `3` semantic, and `0` Steelsearch-only cases. Latest focused ML report is `failed=0`, `missing=0`, `canonical_equal=27`, and `steelsearch_only=0`. | Covered current cases pass; there are no remaining Steelsearch-only cases in the current broad live comparison profile. |
| REST source inventory fixture coverage | `379/379` in-scope source routes matched by fixtures | Fixture inventory is closed for the current source-derived route set. |
| REST live-required source-route mapping | `379/379` in-scope source routes matched by live-required fixture routes, with `3630` live-required fixture routes and `0` required-suite Steelsearch-only cases | Live-required route mapping is closed for the current source inventory. |
| REST source statuses | `implemented=379`, `out-of-scope=10` | Source-derived route classification is closed, while full positive/negative live comparison still needs to expand across the route surface. |
| Transport source inventory | `174` accepted transport evidence rows plus `174/174` source-derived actions with release-parity runtime evidence | Implemented means the declared subset has evidence; broad transport action claims require the separate release ledger to cover each source-derived action. |

Conclusion: the current E2E evidence proves there are no failures or unresolved
skips in the required live comparison profile, and the in-scope source-derived
REST routes are all matched by live-required fixtures. It does not prove
exhaustive OpenSearch API compatibility. To make that broader claim, each
surface still needs semantic-depth evidence for its supported parameter space,
negative-path coverage for unsupported shapes, and operational evidence for
durability, load, packaging, and upgrade readiness.

## 2026-06-28 Route-Parity Refresh

The root/cluster/node route-parity subset was rerun against live Steelsearch and
OpenSearch targets at
`target/route-parity-cluster-health-current-20260628/compare`.

Current rerun result:

| Suite | Passed | Failed |
| --- | ---: | ---: |
| `cluster-health` | 9 | 0 |
| `allocation-explain` | 2 | 0 |
| `cluster-settings` | 8 | 0 |
| `cluster-state` | 19 | 0 |
| `root-cluster-node` | 12 | 0 |
| `tasks` | 14 | 0 |
| `stats` | 12 | 0 |

This refresh converts the previously stale/missing route-parity evidence for
cluster-health invalid parameters, cluster-state validation, task validation,
and stats validation into current live comparison evidence. It does not change
the broader exhaustive-compatibility conclusion above.

## Fixed In This Pass

| Case | Resolution |
| --- | --- |
| `query_string_search` | Source-aware fallback now matches nested/object/array string leaves across default fields. |
| `simple_query_string_search` | Same fallback coverage as `query_string_search`. |
| `rescore_search` | Sort plus rescore now fails closed with OpenSearch-compatible 400. |
| `allow_no_indices_empty_wildcard_search` | Empty resolved target sets no longer fall through to the native all-index search path. |
| `expand_wildcards_none_empty_search` | Same empty-target native-path guard. |
| `top_hits_sorted_aggregation` | Fixture now adds a deterministic secondary sort for tied `ts` values. |
| `expand_wildcards_open_search` | Fixture now compares total/status only because unsorted top-N hit order across expanded indices is not a stable semantic check. |
| `settings_global_named_readback` | Global settings readback now excludes hidden indices by default. |
| `cat_count_json` / `cat_count_text` | Cat count now excludes hidden-index documents by default. |
| `index_stats_shape` | Global stats now excludes hidden indices, SteelSearch-only case-created indices are cleaned up, and delete wildcard handling keeps visible indices when `expand_wildcards=hidden`. |
| `cluster_state_readback` | Cluster-state metadata aliases now match OpenSearch's alias-name array shape, and started routing shards no longer emit `recovery_source`. |
| `significant_terms_aggregation` / `significant_terms_background_filter_aggregation` | Fallback search aggregation now emits bounded significant terms buckets and honors OpenSearch's default `min_doc_count` threshold for this profile. |
| canonical `cat_*_selected_alias_columns` | Selected-column comparison now normalizes volatile cluster/shard values and row ordering while preserving column alias coverage. |
| `segments_target_shape` | Segment shape comparison now excludes the volatile committed flag and keeps index/segment shape coverage. |
| `search_template_*_get_summary` / `msearch_template_*_get_summary` | Template summary requests now include deterministic `ts` sorting before comparing the top hits. |
| `msearch_template_named_root_search` | The fixture now installs the named mustache script before named template execution, so the case compares actual template execution instead of missing-script error drift. |
| `search-strict` unified collection | The unified collector now accepts the generic `search-compat-report.json` emitted by the shared harness when the embedded fixture path matches `search-strict-compat.json`. |
| `search-strict` targeted evidence merge | The unified collector now also accepts explicit `search-strict` targeted report aliases, so quoted `query_string` and `simple_query_string` phrase evidence is merged instead of surfacing as stale missing cases. |
| remote REST PIT transport forwarding | `multi-node-transport-admin` now requires the remote PIT open/search/close/search-after-close/list-after-close cases, and `mixed-cluster-coverage-current` fails if those transport-forwarding cases are absent or not passed. |
| `multi-node-transport-admin` OpenSearch evidence | The suite now accepts an OpenSearch baseline URL, compares all 15 cases against that baseline, and records remote PIT close/search-after-close/list-after-close as `canonical_equal`. |

## Next Fix Order

No remaining failed search-compat/search-strict cases in the latest live run.
