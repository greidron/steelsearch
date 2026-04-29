# REST Compatibility Notes

This note records the current REST MVP comparison against the local Java
OpenSearch checkout at `../OpenSearch`. It is a source-level comparison because
this repository does not yet contain a reproducible live Java REST fixture.

## Source References

Representative MVP routes are registered by these OpenSearch handlers:

| SteelSearch route | Java OpenSearch source | Comparison result |
| --- | --- | --- |
| `GET /` | `server/src/main/java/org/opensearch/rest/action/RestMainAction.java` | Same route and `200` status target. SteelSearch returns the core identity fields used by OpenSearch clients: `name`, `cluster_name`, `cluster_uuid`, `version`, and `tagline`. Build metadata is currently placeholder text. |
| `HEAD /` | `server/src/main/java/org/opensearch/rest/action/RestMainAction.java` | Same route and `200` status target. SteelSearch returns an empty body. |
| `GET /_cluster/health` | `server/src/main/java/org/opensearch/rest/action/admin/cluster/RestClusterHealthAction.java` | Same base route and `200` status target. SteelSearch emits the top-level health counters needed by the REST shell: `cluster_name`, `status`, `timed_out`, node counts, shard counts, pending task counters, and active shard percentage. Index-scoped health and wait parameters are not implemented yet. |
| `PUT /{index}` | `server/src/main/java/org/opensearch/rest/action/admin/indices/RestCreateIndexAction.java` | Same route and success status target. SteelSearch returns `acknowledged`, `shards_acknowledged`, and `index`; duplicate index names return an OpenSearch-shaped `resource_already_exists_exception`. Request body parsing and mappings/settings application are deferred. |
| `GET /{index}` | `server/src/main/java/org/opensearch/rest/action/admin/indices/RestGetIndicesAction.java` | Same `GET /{index}` route and success status target. SteelSearch returns per-index `aliases`, `mappings`, and `settings.index` fields for the MVP registry, including comma and wildcard read expansion for registered indices. Missing index names return an OpenSearch-shaped `index_not_found_exception`. `HEAD /{index}` is not implemented yet. |
| `DELETE /{index}` | `server/src/main/java/org/opensearch/rest/action/admin/indices/RestDeleteIndexAction.java` | Same route and success status target. SteelSearch returns `acknowledged`; missing index names return an OpenSearch-shaped `index_not_found_exception`. `DELETE /` wildcard behavior is not implemented. |
| `GET/POST /_search`, `GET/POST /{index}/_search` | `server/src/main/java/org/opensearch/rest/action/search/RestSearchAction.java` | SteelSearch supports the selected query, sort, pagination, aggregation, alias/wildcard target expansion, `ignore_unavailable`, `allow_no_indices`, and `expand_wildcards=open/all/none` subset used by the compatibility fixture. Advanced OpenSearch features, response-shaping options, unsupported Query DSL families, unsupported aggregation families/options, and closed/hidden wildcard expansion that would otherwise be silently ignored now fail closed with OpenSearch-shaped error responses. |
| Alias and template persistence | `server/src/main/java/org/opensearch/rest/action/admin/indices/alias/RestIndexPutAliasAction.java`, `server/src/main/java/org/opensearch/rest/action/admin/indices/alias/RestGetAliasesAction.java`, `server/src/main/java/org/opensearch/rest/action/admin/indices/alias/RestIndexDeleteAliasesAction.java`, `server/src/main/java/org/opensearch/rest/action/admin/indices/template/put/RestPutComposableIndexTemplateAction.java`, `server/src/main/java/org/opensearch/rest/action/admin/cluster/RestPutComponentTemplateAction.java` | SteelSearch now has alias mutation, `_aliases` readback, dedicated alias `GET /_alias/{alias}` and `GET /{index}/_alias/{alias}` readback with wildcard alias-name matching, alias-backed `_search` resolution, and alias-backed single-document reads/writes when the alias resolves to one concrete index or one write index. It also has a focused comparison fixture for alias/template registry persistence across restart and snapshot restore. See `tools/fixtures/alias-template-persistence-compat.json` and `docs/rust-port/alias-template-persistence-compatibility.md`. |
| Data streams and rollover | `server/src/main/java/org/opensearch/rest/action/admin/indices/datastream/RestCreateDataStreamAction.java`, `server/src/main/java/org/opensearch/rest/action/admin/indices/datastream/RestGetDataStreamsAction.java`, `server/src/main/java/org/opensearch/rest/action/admin/indices/rollover/RestRolloverIndexAction.java` | SteelSearch explicitly rejects data stream templates, top-level create-index `data_stream` bodies, `/_data_stream` APIs, and rollover-style routes with OpenSearch-shaped `illegal_argument_exception` responses until backing-index generation and lifecycle semantics are implemented. |

## Current Test Coverage

`crates/os-node/src/lib.rs` has compatibility tests for:

- representative success status codes and JSON field shapes;
- OpenSearch-shaped error envelopes for duplicate and missing indices;
- node lifecycle rejection when REST is stopped.
- alias/template registry persistence across development metadata restart and
  snapshot restore, backed by a documented OpenSearch comparison fixture.
- executable Steelsearch/OpenSearch comparison coverage for index `HEAD`,
  index alias/settings readback, wildcard index read expansion, dedicated alias
  `GET` readback, `_aliases` readback, wildcard alias-name readback,
  alias-backed document reads/writes, alias-backed search, wildcard search
  expansion, `_cat/indices?format=json`, `_nodes/stats`, `_cluster/stats`,
  `_stats`, `_tasks`, and Steelsearch-only development allocation explain
  output.
- explicit fail-closed data stream and rollover route decisions, including
  create-index body rejection and Steelsearch-only fixture skips for unsupported
  OpenSearch data stream APIs.
- explicit fail-closed search request validation for unsupported advanced
  OpenSearch features, including highlight, rescore, collapse, suggest, PIT,
  scroll, and search-after.
- explicit fail-closed search response option validation for `track_total_hits`,
  `terminate_after`, `timeout`, `explain`, `profile`, `stored_fields`, and
  `docvalue_fields`.
- explicit fail-closed Query DSL family validation for unsupported compound and
  specialized queries, including query-string, function/script score, nested,
  geo, regexp, fuzzy, more-like-this, and span query families.
- multi-target search option coverage for `ignore_unavailable`,
  `allow_no_indices`, and `expand_wildcards=open/all/none`, with closed/hidden
  wildcard expansion rejected until closed-index state exists.
- explicit fail-closed aggregation validation for unsupported aggregation
  families such as date_histogram, histogram, range, and cardinality, plus
  unsupported options on implemented aggregation families.
- executable aggregation comparison fixtures for implemented metrics, filter,
  filters, top_hits, composite, significant_terms, geo_bounds, sum_bucket, and
  documented Steelsearch-only scripted/plugin aggregation surfaces.
- explicit skip reporting in the REST comparison summary for intentional
  OpenSearch divergence and unsupported query-parameter semantics, including
  cat text formatting, health wait parameters, and development allocation
  explain behavior.
- CI/report assertions through `tools/check-rest-compat-report.py`, which
  validates fixture skip contracts and generated report drift for missing,
  extra, failed, or newly skipped cases.
- CI artifact generation through the `Source compatibility drift` workflow's
  manual and weekly scheduled REST compatibility report job. The job runs
  `tools/run-rest-compat-ci-report.sh`, starts local Steelsearch/OpenSearch
  services when URLs are not supplied, and uploads the full `target/rest-compat`
  artifact directory including `search-compat-report.json`, target URLs,
  service logs, per-case summaries, and normalized aggregation diffs. Scheduled
  artifacts are retained for 7 days to cap storage cost. Failed scheduled or
  manual report runs write a job-summary triage block that links the workflow
  run, uploaded artifact, report JSON, target metadata, and service logs. The
  artifact `targets.env` records Steelsearch/OpenSearch startup durations and
  the CI wait timeout so the first scheduled run can be tuned from evidence.

## Deferred Live Comparison

Live Java REST response capture remains part of the cross-cutting interop work.
It should be added once the Rust HTTP server can be exercised over an actual
socket and a local Java OpenSearch node can be started reproducibly from the
same test harness.
