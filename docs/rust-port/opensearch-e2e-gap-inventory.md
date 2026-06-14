# OpenSearch E2E Gap Inventory

This inventory covers the remaining live OpenSearch comparison failures after
fixture cleanup and composable-template create-index support.

Latest report:
`target/opensearch-e2e-search-compat-fixture-audit-current/report/unified-opensearch-e2e-report.json`

## Summary

- Total remaining failed rows: 25.
- Unique remaining case names: 14.
- Repeated in both `search-compat` and `search-strict`: 11 cases.
- Strict-only: `cat_count_json`, `cat_count_text`.
- Basic-only: `index_stats_shape`.

## Remaining Gaps

| Case | Suites | Classification | Evidence |
| --- | --- | --- | --- |
| `query_string_search` | basic, strict | Real search semantics gap | OpenSearch returns `log-1`, `log-4`, `log-2`; SteelSearch returns `log-1`, `log-2`. |
| `simple_query_string_search` | basic, strict | Real search semantics gap | Same missing `log-4` pattern as query string. |
| `rescore_search` | basic, strict | Real search semantics gap | SteelSearch accepts or scores a rescore request differently from OpenSearch. This needs either compatible rescore behavior or a fail-closed path for unsupported combinations. |
| `significant_terms_aggregation` | basic, strict | Real aggregation gap | Significant terms output does not match OpenSearch. |
| `significant_terms_background_filter_aggregation` | basic, strict | Real aggregation gap | Significant terms with background filter does not match OpenSearch. |
| `top_hits_sorted_aggregation` | basic, strict | Aggregation/fetch ordering gap | Top hits aggregation sorted payload differs from OpenSearch. |
| `allow_no_indices_empty_wildcard_search` | basic, strict | Target option semantics gap | Empty wildcard behavior under `allow_no_indices` does not match OpenSearch. |
| `expand_wildcards_none_empty_search` | basic, strict | Target option semantics gap | `expand_wildcards=none` behavior on empty wildcard does not match OpenSearch. |
| `expand_wildcards_open_search` | basic, strict | Search target/order normalization gap | Total count matches, but first-page ids differ across expanded indices. This may need explicit OpenSearch-compatible index ordering or fixture-side sort if the case is meant to ignore cross-index order. |
| `settings_global_named_readback` | basic, strict | Index visibility/settings gap | SteelSearch includes hidden target/delete indices that OpenSearch omits for this request shape. |
| `cluster_state_readback` | basic, strict | Cluster-state shape gap | SteelSearch reports alias and recovery-source presence differently from OpenSearch. |
| `cat_count_json` | strict only | Strict fixture isolation/visibility candidate | Basic suite passes, but strict count differs. The likely cause is strict-mode global index visibility or setup residue rather than document count in the primary search index. |
| `cat_count_text` | strict only | Strict fixture isolation/visibility candidate | Same as `cat_count_json`. |
| `index_stats_shape` | basic only | Operational stats shape gap | Index stats extracted shape still differs from OpenSearch. |

## Next Fix Order

1. Query-string and simple-query-string parsing/matching, because these are
   direct user-visible search correctness gaps.
2. Unsupported target option behavior for empty wildcard and
   `expand_wildcards=none`, preferably fail-closed if full compatibility is not
   ready.
3. Significant terms and top-hits aggregation parity.
4. Hidden/deleted index visibility in settings, cat count, and stats APIs.
5. Cluster-state response shape normalization for aliases and recovery source.
