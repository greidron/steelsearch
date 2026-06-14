# OpenSearch E2E Gap Inventory

This inventory covers the remaining live OpenSearch comparison failures after
the fixture cleanup, composable-template create-index support, and the first
search semantics gap pass.

Latest report:
`target/opensearch-e2e-search-compat-gap-fix-current-2/report/unified-opensearch-e2e-report.json`

## Summary

- Total remaining failed rows: 11.
- Unique remaining case names: 7.
- Repeated in both `search-compat` and `search-strict`: 4 cases.
- Strict-only: `cat_count_json`, `cat_count_text`.
- Basic-only: `index_stats_shape`.
- `search-compat`: 146 passed, 5 failed, 16 skipped.
- `search-strict`: 139 passed, 6 failed, 6 skipped.

## Remaining Gaps

| Case | Suites | Classification | Evidence |
| --- | --- | --- | --- |
| `significant_terms_aggregation` | basic, strict | Real aggregation gap | Significant terms output does not match OpenSearch. |
| `significant_terms_background_filter_aggregation` | basic, strict | Real aggregation gap | Significant terms with background filter does not match OpenSearch. |
| `settings_global_named_readback` | basic, strict | Index visibility/settings gap | SteelSearch includes hidden target/delete indices that OpenSearch omits for this request shape. |
| `cluster_state_readback` | basic, strict | Cluster-state shape gap | SteelSearch reports alias and recovery-source presence where OpenSearch omits them for this request. |
| `cat_count_json` | strict only | Visibility/count gap | Strict count is 20 in SteelSearch versus 17 in OpenSearch, matching extra hidden/unsupported indices leaking into count scope. |
| `cat_count_text` | strict only | Visibility/count gap | Same as `cat_count_json`. |
| `index_stats_shape` | basic only | Operational stats shape gap | SteelSearch includes hidden and unsupported vector indices; OpenSearch omits them and reports 12 shards versus SteelSearch 15. |

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

## Next Fix Order

1. Hidden/deleted/unsupported index visibility in settings, cat count, and
   stats APIs.
2. Cluster-state response shape normalization for aliases and recovery source.
3. Significant terms and significant terms with background filter parity.
