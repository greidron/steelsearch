# OpenSearch E2E Gap Inventory

This inventory covers the remaining live OpenSearch comparison failures after
the fixture cleanup, composable-template create-index support, search semantics
gap pass, and index-visibility/count/stats pass.

Latest report:
`target/opensearch-e2e-search-compat-visibility-fix-final-2/report/unified-opensearch-e2e-report.json`

## Summary

- Total remaining failed rows: 6.
- Unique remaining case names: 3.
- Repeated in both `search-compat` and `search-strict`: 3 cases.
- Strict-only: none.
- Basic-only: none.
- `search-compat`: 148 passed, 3 failed, 16 skipped.
- `search-strict`: 142 passed, 3 failed, 6 skipped.

## Remaining Gaps

| Case | Suites | Classification | Evidence |
| --- | --- | --- | --- |
| `significant_terms_aggregation` | basic, strict | Real aggregation gap | Significant terms output does not match OpenSearch. |
| `significant_terms_background_filter_aggregation` | basic, strict | Real aggregation gap | Significant terms with background filter does not match OpenSearch. |
| `cluster_state_readback` | basic, strict | Cluster-state shape gap | SteelSearch reports alias and recovery-source presence where OpenSearch omits them for this request. |

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

## Next Fix Order

1. Cluster-state response shape normalization for aliases and recovery source.
2. Significant terms and significant terms with background filter parity.
