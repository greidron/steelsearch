# OpenSearch E2E Fixture Issues

This note separates harness and fixture problems from SteelSearch/OpenSearch
semantic gaps in the search compatibility suites.

## Baseline

- Initial unified comparison: 53 failed cases across `search-compat` and
  `search-strict`.
- After fixture, harness, and one confirmed SteelSearch template fix:
  25 failed cases remain.
- After the first search semantics gap pass:
  11 failed cases remain.
- After the index visibility/count/stats pass:
  6 failed cases remain.
- After the cluster-state shape pass:
  4 failed cases remain.
- After the significant-terms pass:
  0 failed cases remain.
- Latest live run:
  `target/opensearch-e2e-search-compat-significant-terms-fix-2/report/unified-opensearch-e2e-report.json`
- Latest command profile: `search-compat` plus `search-strict` against live
  local SteelSearch and OpenSearch endpoints.

## Confirmed Fixture Or Harness Issues

| Issue | Why it was not a real SteelSearch semantic failure | Fix |
| --- | --- | --- |
| Index template setup before component template setup | OpenSearch rejected the index template because the referenced component template did not exist yet. | Create component templates before composable index templates. |
| Request-created indices leaking between strict/basic suite runs | Some setup `PUT /{index}` requests created indices outside the declared fixture index list, so repeated runs reused stale state. | Cleanup now deletes data streams, templates, component templates, and indices inferred from setup requests. |
| Request-created templated index created before templates existed | `logs-template-000001` could not receive composable template aliases/mappings when it was created before templates were installed. | Run fixture `requests` after templates and data streams, then refresh. |
| `_analyze` fixture used GET query text | Current OpenSearch target requires request body or `source` for these analyzer calls. | Changed analyzer fixtures to `POST /_analyze` and `POST /{index}/_analyze` with JSON bodies. |
| k-NN and ML cases compared against an OpenSearch target without plugin REST handlers | OpenSearch returned `no handler found for uri` for plugin endpoints in this environment. | Treat missing plugin handlers as degraded-source skips for k-NN/ML comparisons. |
| Data stream stats compared volatile byte counters exactly | Store-size byte values are environment and timing dependent. | Compare store-size presence rather than exact `total_store_size_bytes`. |
| Field/highlight search cases depended on hit order only | The compared values were otherwise equal, but order could differ without semantic significance for those extractors. | Sort extracted ids for `search_fields` and `highlight_hits`. |
| `top_hits_sorted_aggregation` had tied primary sort values | OpenSearch returned `log-4` and SteelSearch returned `log-alias` for the same `ts` sort value; both were valid without a tie-breaker. | Add secondary `bytes desc` sort to make the expected top hit deterministic. |
| `expand_wildcards_open_search` compared unsorted top-N hits | Both engines returned total 8, but the first two hits differed because the request had no sort across expanded indices. | Compare status/total only for this target-expansion fixture. |
| SteelSearch-only k-NN case indices leaked into later stats/settings checks | Unsupported-option cases intentionally run only against SteelSearch, so their case-local `PUT /{index}` steps left indices that OpenSearch never created. | Cleanup now deletes case-step-created indices before fixture setup and after SteelSearch-only cases. |

## Confirmed SteelSearch Fix From This Audit

`templated_index_application_readback` and `get_aliases_readback` exposed a real
SteelSearch gap: direct `PUT /logs-template-000001` did not apply matching
composable index templates and component templates. SteelSearch now merges
matching component template and index template `template` blocks into the index
manifest before creating the native index.

The focused regression tests include
`create_index_applies_matching_composable_and_component_templates`,
`delete_index_hidden_wildcard_only_removes_hidden_targets`,
`index_stats_routes_serve_global_metric_and_targeted_shapes`, and
`named_settings_routes_filter_global_and_targeted_setting_keys`.

This pass also fixed real SteelSearch visibility gaps: global settings, cat
count, and global stats now omit hidden indices by default, and wildcard delete
with `expand_wildcards=hidden` no longer removes visible indices.
The cluster-state pass fixed another real SteelSearch shape gap: metadata
aliases now use OpenSearch's alias-name array shape, and started routing shards
no longer include `recovery_source`.
The significant-terms pass fixed the remaining aggregation gap in the fallback
search route: bounded `significant_terms` buckets are now emitted, including the
`background_filter: match_all` case covered by the search fixtures.

## Result

The failed count moved from 53 to 0:

- `search-compat`: 152 passed, 0 failed, 15 skipped.
- `search-strict`: 146 passed, 0 failed, 5 skipped.
- Remaining failed rows: 0.

No failed cases remain in the latest live `search-compat` plus `search-strict`
comparison profile. Skips are tracked by explicit skip scopes in the reports.
