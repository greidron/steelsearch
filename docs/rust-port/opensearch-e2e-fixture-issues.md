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
- Latest live run:
  `target/opensearch-e2e-search-compat-gap-fix-current-2/report/unified-opensearch-e2e-report.json`
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

## Confirmed SteelSearch Fix From This Audit

`templated_index_application_readback` and `get_aliases_readback` exposed a real
SteelSearch gap: direct `PUT /logs-template-000001` did not apply matching
composable index templates and component templates. SteelSearch now merges
matching component template and index template `template` blocks into the index
manifest before creating the native index.

The focused regression test is
`create_index_applies_matching_composable_and_component_templates`.

## Result

The failed count moved from 53 to 11:

- `search-compat`: 146 passed, 5 failed, 16 skipped.
- `search-strict`: 139 passed, 6 failed, 6 skipped.
- Unified classification: 146 canonical equal, 139 strict equal,
  22 known gap or skipped, 11 failed.

The remaining 11 failures are not explained by the fixed setup issues. They are
tracked in `opensearch-e2e-gap-inventory.md`.
