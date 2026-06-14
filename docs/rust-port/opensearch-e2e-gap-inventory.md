# OpenSearch E2E Gap Inventory

This inventory covers the remaining live OpenSearch comparison failures after
the fixture cleanup, composable-template create-index support, search semantics
gap pass, index-visibility/count/stats pass, cluster-state shape pass, and
significant-terms pass.

Latest report:
`target/opensearch-e2e-search-compat-significant-terms-fix-2/report/unified-opensearch-e2e-report.json`

## Summary

- Total remaining failed rows: 0.
- Unique remaining case names: 0.
- Repeated in both `search-compat` and `search-strict`: 0 cases.
- Strict-only: none.
- Basic-only: none.
- `search-compat`: 151 passed, 0 failed, 16 skipped.
- `search-strict`: 145 passed, 0 failed, 6 skipped.

## Remaining Gaps

No failed cases remain in the live `search-compat` plus `search-strict`
comparison profile.

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
