# OpenSearch E2E Gap Inventory

This inventory covers the remaining live OpenSearch comparison failures after
the fixture cleanup, composable-template create-index support, search semantics
gap pass, index-visibility/count/stats pass, cluster-state shape pass, and
significant-terms pass.

Latest report:
`target/unified-opensearch-e2e-current/unified-opensearch-e2e-report.json`

Latest audit report:
`target/unified-opensearch-e2e-audit/unified-opensearch-e2e-report.json`

## Summary

- Total remaining failed rows: 0.
- Unique remaining case names: 0.
- Repeated in both `search-compat` and `search-strict`: 0 cases.
- Strict-only: none.
- Basic-only: none.
- `search-compat`: 226 passed, 0 failed, 20 skipped.
- `search-strict`: 146 passed, 0 failed, 5 skipped.
- `search-semantic`: 49 passed, 0 failed, 0 skipped.
- `vector-search`: 16 passed, 0 failed, 0 skipped.
- Combined required classification:
  `canonical_equal=287`, `strict_equal=146`, `semantic_equal=4`,
  `failed=0`, `missing=0`.

## Remaining Gaps

No failed cases remain in the live `search-compat` plus `search-strict`
comparison profile.

## Exhaustive API Compatibility Audit

Current generated reports:

- `target/rest-api-coverage-head.json`
- `target/transport-action-coverage-head.json`
- `target/unified-opensearch-e2e-current/unified-opensearch-e2e-report.json`

Current status:

| Area | Current evidence | Exhaustive-compatibility result |
| --- | --- | --- |
| Live required OpenSearch E2E suites | `failed=0`, `missing=0`, `known_gap_or_skipped=25` across `226` canonical and `146` strict equal cases | Covered cases pass, but skipped/deferred cases remain. |
| REST source inventory fixture coverage | `371/371` in-scope source routes matched by fixtures | Fixture inventory is closed, but this is not the same as positive/negative live comparison for every route. |
| REST live-required source-route mapping | `130/371` in-scope source routes matched by live-required fixture routes | Live-required coverage is representative, not exhaustive. |
| REST source statuses | `implemented=2`, `stubbed=6`, `planned=363`, `out-of-scope=18` | Most source-derived rows still need owner-level implementation classification. |
| Transport source inventory | `160` transport actions: `33 implemented`, `127 partial`, `0 planned` | Implemented adapters have positive wire/route evidence; partial rows have explicit fail-closed boundaries and still need per-action execution semantics plus live comparison evidence. |

Conclusion: the current E2E evidence proves there are no failures in the
required live comparison profile. It does not prove exhaustive OpenSearch API
compatibility. To make that claim, every in-scope source-derived REST route and
transport action still needs an owner-level implementation classification plus
positive and negative live comparison evidence, or an explicit out-of-scope
decision.

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

## Next Fix Order

No remaining failed search-compat/search-strict cases in the latest live run.
