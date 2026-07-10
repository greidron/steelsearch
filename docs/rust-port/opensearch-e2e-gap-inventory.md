# OpenSearch E2E Gap Inventory

This inventory covers the remaining live OpenSearch comparison failures after
the fixture cleanup, composable-template create-index support, search semantics
gap pass, index-visibility/count/stats pass, cluster-state shape pass, and
significant-terms pass.

Latest report:
`target/unified-opensearch-e2e-broad-current/unified-opensearch-e2e-report.json`

Latest audit report:
`target/unified-opensearch-e2e-audit/unified-opensearch-e2e-report.json`

## Summary

- Total remaining failed rows: 0.
- Unique remaining case names: 0.
- Repeated in both `search-compat` and `search-strict`: 0 cases.
- Strict-only: none.
- Basic-only: none.
- `search-compat`: 1011 passed, 0 failed, 17 skipped.
- `search-strict`: 850 passed, 0 failed, 5 skipped.
- `search-semantic`: 75 passed, 0 failed, 0 skipped.
- `runtime-stateful-probe`: 519 passed, 0 failed, 0 skipped; 24 cases now
  carry case-level OpenSearch route-presence comparison evidence.
- `vector-search`: 25 passed, 0 failed, 0 skipped.
- `vector-search-native-surface`: 25 passed, 0 failed, 0 skipped.
- `knn-plugin-surface`: 8 passed, 0 failed, 0 skipped.
- `ml-model-surface`: 27 passed, 0 failed.
- `multi-node-transport-admin`: 15 passed, 0 failed, including remote REST PIT
  search/close forwarding through the transport path.
- Combined required classification:
  `canonical_equal=1497`, `strict_equal=937`, `semantic_equal=0`,
  `steelsearch_fail_closed=1`, `steelsearch_only=632`,
  `known_gap_or_skipped=22`, `failed=0`, `missing=0`.
- Effective required classification after skip resolution:
  `known_gap_or_skipped=0`; all 22 raw skipped cases are covered by other
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
| Live required OpenSearch E2E suites | `failed=0`, `missing=0`, raw `known_gap_or_skipped=22`, effective `known_gap_or_skipped=0` across `1497` canonical, `937` strict, `632` Steelsearch-only, and `1` Steelsearch fail-closed cases | Covered cases pass, and raw skipped cases are resolved by other required suites. |
| REST source inventory fixture coverage | `378/378` in-scope source routes matched by fixtures | Fixture inventory is closed for the current source-derived route set. |
| REST live-required source-route mapping | `378/378` in-scope source routes matched by live-required fixture routes, with `3480` live-required fixture routes | Live-required route mapping is closed for the current source inventory. |
| REST source statuses | `implemented=378`, `out-of-scope=11` | Source-derived route classification is closed, while full positive/negative live comparison still needs to expand across the route surface. |
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

## Next Fix Order

No remaining failed search-compat/search-strict cases in the latest live run.
