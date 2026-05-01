# Generated Route Evidence Matrix

This file maps each source-derived REST route to its current Steelsearch
status and the canonical comparison/profile owner when one exists.

| family | status | method | path_or_expression | evidence_profile | evidence_entrypoint |
| --- | --- | --- | --- | --- | --- |
| snapshot-migration-interop | planned | GET | `/_ingest/processor/grok` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/_msearch/template` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/_msearch/template` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/{index}/_msearch/template` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/{index}/_msearch/template` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/_render/template` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/_render/template` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/_render/template/{id}` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/_render/template/{id}` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/_search/template` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/_search/template` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/{index}/_search/template` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/{index}/_search/template` | `deferred` | `no canonical runtime compare owner` |
| snapshot-migration-interop | planned | GET | `/_scripts/painless/_context` | `deferred` | `no canonical runtime compare owner` |
| snapshot-migration-interop | planned | GET | `/_scripts/painless/_execute` | `deferred` | `no canonical runtime compare owner` |
| snapshot-migration-interop | planned | POST | `/_scripts/painless/_execute` | `deferred` | `no canonical runtime compare owner` |
| misc | planned | (dynamic) | `/_opensearch_dashboards + route.getPath(` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/ + ENDPOINT` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/ + ENDPOINT` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/{index}/ + ENDPOINT` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/{index}/ + ENDPOINT` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/{index}/_delete_by_query` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/_reindex` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/_update_by_query/{taskId}/_rethrottle` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/_delete_by_query/{taskId}/_rethrottle` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/_reindex/{taskId}/_rethrottle` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/{index}/_update_by_query` | `deferred` | `no canonical runtime compare owner` |
| misc | out-of-scope | GET | `/_flight/stats` | `deferred` | `no canonical runtime compare owner` |
| misc | out-of-scope | GET | `/_flight/stats/{nodeId}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | out-of-scope | GET | `/_nodes/flight/stats` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | out-of-scope | GET | `/_nodes/{nodeId}/flight/stats` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | out-of-scope | GET | `/_cat/example` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | out-of-scope | POST | `/_cat/example` | `deferred` | `no canonical runtime compare owner` |
| misc | out-of-scope | PUT | `/_steelsearch/persistent_task/{task_id}` | `deferred` | `no canonical runtime compare owner` |
| misc | out-of-scope | DELETE | `/_steelsearch/persistent_task/{task_id}` | `deferred` | `no canonical runtime compare owner` |
| misc | out-of-scope | POST | `/test/_stream` | `deferred` | `no canonical runtime compare owner` |
| misc | out-of-scope | POST | `_wlm/workload_group/` | `deferred` | `no canonical runtime compare owner` |
| misc | out-of-scope | PUT | `_wlm/workload_group/` | `deferred` | `no canonical runtime compare owner` |
| misc | out-of-scope | DELETE | `_wlm/workload_group/{name}` | `deferred` | `no canonical runtime compare owner` |
| misc | out-of-scope | GET | `_wlm/workload_group/` | `deferred` | `no canonical runtime compare owner` |
| misc | out-of-scope | GET | `_wlm/workload_group/{name}` | `deferred` | `no canonical runtime compare owner` |
| misc | out-of-scope | POST | `_wlm/workload_group/{name}` | `deferred` | `no canonical runtime compare owner` |
| misc | out-of-scope | PUT | `_wlm/workload_group/{name}` | `deferred` | `no canonical runtime compare owner` |
| misc | planned | GET | `/_field_caps` | `deferred` | `no canonical runtime compare owner` |
| misc | planned | POST | `/_field_caps` | `deferred` | `no canonical runtime compare owner` |
| misc | planned | GET | `/{index}/_field_caps` | `deferred` | `no canonical runtime compare owner` |
| misc | planned | POST | `/{index}/_field_caps` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented | GET | `/` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | HEAD | `/` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | planned | POST | `/_cluster/voting_config_exclusions` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented-stateful | POST | `/_tasks/_cancel` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | planned | POST | `/_tasks/{task_id}/_cancel` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | POST | `/_snapshot/{repository}/_cleanup` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | DELETE | `/_cluster/voting_config_exclusions` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | PUT | `/_snapshot/{repository}/{snapshot}/_clone/{target_snapshot}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented-read | GET | `/_cluster/allocation/explain` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | planned | POST | `/_cluster/allocation/explain` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | DELETE | `/_cluster/routing/awareness/weights` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | DELETE | `/_cluster/routing/awareness/{attribute}/weights` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented-read | GET | `/_cluster/settings` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/routing/awareness/{attribute}/weights` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/health` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/health/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | planned | PUT | `/_cluster/routing/awareness/{attribute}/weights` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | POST | `/_cluster/reroute` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_search_shards` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | POST | `/_search_shards` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/{index}/_search_shards` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | POST | `/{index}/_search_shards` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented-read | GET | `/_cluster/state` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/state/{metric}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/state/{metric}/{indices}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/stats` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | planned | GET | `/_cluster/stats/nodes/{nodeId}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_cluster/stats/{metric}/nodes/{nodeId}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_cluster/stats/{metric}/{index_metric}/nodes/{nodeId}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented-stateful | PUT | `/_cluster/settings` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | planned | POST | `/_snapshot/{repository}/{snapshot}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | PUT | `/_snapshot/{repository}/{snapshot}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | PUT | `/_cluster/decommission/awareness/{awareness_attribute_name}/{awareness_attribute_value}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | DELETE | `/_cluster/decommission/awareness` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | DELETE | `/_snapshot/{repository}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | DELETE | `/_snapshot/{repository}/{snapshot}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | DELETE | `/_scripts/{id}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented-read | GET | `/_cluster/decommission/awareness/{awareness_attribute_name}/_status` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_snapshot` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_snapshot/{repository}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | planned | GET | `/_script_context` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_script_language` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented-read | GET | `/_snapshot/{repository}/{snapshot}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | planned | GET | `/_scripts/{id}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented-read | GET | `/_tasks/{task_id}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_tasks` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | planned | GET | `/_nodes/hot_threads` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_nodes/{nodeId}/hot_threads` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_nodes` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_nodes/{nodeId}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_nodes/{nodeId}/{metrics}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_nodes/{nodeId}/info/{metrics}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented-read | GET | `/_nodes/stats` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | planned | GET | `/_nodes/{nodeId}/stats` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_nodes/stats/{metric}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_nodes/{nodeId}/stats/{metric}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_nodes/stats/{metric}/{index_metric}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_nodes/{nodeId}/stats/{metric}/{index_metric}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_nodes/usage` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_nodes/{nodeId}/usage` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_nodes/usage/{metric}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_nodes/{nodeId}/usage/{metric}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented-read | GET | `/_cluster/pending_tasks` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | planned | POST | `/_filecache/prune` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | POST | `/_snapshot/{repository}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented-stateful | PUT | `/_snapshot/{repository}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | planned | POST | `/_scripts/{id}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | PUT | `/_scripts/{id}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | POST | `/_scripts/{id}/{context}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | PUT | `/_scripts/{id}/{context}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | POST | `/_nodes/reload_secure_settings` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | POST | `/_nodes/{nodeId}/reload_secure_settings` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_remote/info` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_remotestore/metadata/{index}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_remotestore/metadata/{index}/{shard_id}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_remotestore/stats/{index}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_remotestore/stats/{index}/{shard_id}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | POST | `/_remotestore/_restore` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | POST | `/_snapshot/{repository}/{snapshot}/_restore` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_snapshot/{repository}/{snapshot}/{index}/_status` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented-read | GET | `/_snapshot/{repository}/{snapshot}/_status` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_snapshot/{repository}/_status` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_snapshot/_status` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | planned | POST | `/_snapshot/{repository}/_verify` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `_wlm/stats` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `_wlm/{nodeId}/stats` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `_wlm/stats/{workloadGroupId}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `_wlm/{nodeId}/stats/{workloadGroupId}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `_list/wlm_stats` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `_list/wlm_stats/{nodeId}/stats` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `_list/wlm_stats/stats/{workloadGroupId}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `_list/wlm_stats/{nodeId}/stats/{workloadGroupId}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | DELETE | `/_dangling/{index_uuid}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | POST | `/_dangling/{index_uuid}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | GET | `/_dangling` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/{index}/_block/{block}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/_analyze` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_analyze` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/{index}/_analyze` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_analyze` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_cache/clear` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_cache/clear` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_close` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_close` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/_data_stream/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | implemented-stateful | PUT | `/{index}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_data_stream/_stats` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_data_stream/{name}/_stats` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | planned | DELETE | `/_component_template/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | DELETE | `/_index_template/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | DELETE | `/_data_stream/{name}` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | planned | DELETE | `/` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | stubbed | DELETE | `/{index}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | planned | DELETE | `/_template/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/_flush` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_flush` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/{index}/_flush` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_flush` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_forcemerge` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_forcemerge` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | implemented-read | GET | `/_alias` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_aliases` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | HEAD | `/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/{index}/_alias` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | HEAD | `/{index}/_alias` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/{index}/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | HEAD | `/{index}/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_component_template` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_component_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | HEAD | `/_component_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_index_template` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_index_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | HEAD | `/_index_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_data_stream` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_data_stream/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | planned | GET | `/_mapping/field/{fields}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/{index}/_mapping/field/{fields}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | implemented-read | GET | `/_template` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | HEAD | `/_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/{index}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | HEAD | `/{index}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | planned | GET | `/{index}/ingestion/_state` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | implemented-read | GET | `/_mapping` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | planned | GET | `/_mappings` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | implemented-read | GET | `/{index}/_mapping` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | planned | GET | `/{index}/_mappings` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | implemented-read | GET | `/_settings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | planned | GET | `/_settings/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | implemented-read | GET | `/{index}/_settings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | planned | GET | `/{index}/_settings/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/{index}/_setting/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | DELETE | `/{index}/_alias/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | DELETE | `/{index}/_aliases/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_alias/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/{index}/_alias/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_alias/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/_alias/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_aliases/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/{index}/_aliases/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_aliases/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/_aliases/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/{index}/_alias` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/{index}/_aliases` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/_alias` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_aliases` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/_segments` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/{index}/_segments` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/_shard_stores` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/{index}/_shard_stores` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | implemented-read | GET | `/_stats` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | planned | GET | `/_stats/{metric}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/{index}/_stats` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/{index}/_stats/{metric}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_open` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_open` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/ingestion/_pause` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_component_template/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/_component_template/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_index_template/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/_index_template/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_template/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/_template/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_mapping` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/{index}/_mapping` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_mappings` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/{index}/_mappings` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/_recovery` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/{index}/_recovery` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | GET | `/_refresh` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/_refresh` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | GET | `/{index}/_refresh` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/{index}/_refresh` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_shrink/{target}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/{index}/_shrink/{target}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_split/{target}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/{index}/_split/{target}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_clone/{target}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/{index}/_clone/{target}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/_resolve/index/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/ingestion/_resume` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_rollover` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_rollover/{new_index}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_scale` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_index_template/_simulate_index/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_index_template/_simulate` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_index_template/_simulate/{name}` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/_flush/synced` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_flush/synced` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/{index}/_flush/synced` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_flush/synced` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/_settings` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | PUT | `/{index}/_settings` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/_upgrade` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | POST | `/{index}/_upgrade` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/_upgrade` | `deferred` | `no canonical runtime compare owner` |
| index-and-metadata | planned | GET | `/{index}/_upgrade` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/_validate/query` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/_validate/query` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/{index}/_validate/query` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/{index}/_validate/query` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented-read | GET | `/_cat/aliases` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/aliases/{alias}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/allocation` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/allocation/{nodes}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | planned | GET | `/_cat` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented-read | GET | `/_cat/recovery` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/recovery/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/count` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/count/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/fielddata` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/fielddata/{fields}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/health` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/indices` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/indices/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/nodeattrs` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/nodes` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/pending_tasks` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/pit_segments` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/pit_segments/_all` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/plugins` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/repositories` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/segments` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/segments/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/shards` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/shards/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/snapshots` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/snapshots/{repository}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/tasks` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/templates` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/templates/{name}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/thread_pool` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/thread_pool/{thread_pool_patterns}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| document-and-bulk | planned | POST | `/_bulk` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | implemented-stateful | POST | `/{index}/_bulk` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | planned | PUT | `/_bulk` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | PUT | `/{index}/_bulk` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/_bulk/stream` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | PUT | `/_bulk/stream` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/{index}/_bulk/stream` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | PUT | `/{index}/_bulk/stream` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | DELETE | `/{index}/_doc/{id}` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | implemented-read | GET | `/{index}/_doc/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-read | HEAD | `/{index}/_doc/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | planned | GET | `/{index}/_source/{id}` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | implemented-read | HEAD | `/{index}/_source/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | planned | POST | `/{index}/_doc/{id}` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | stubbed | PUT | `/{index}/_doc/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | planned | POST | `/{index}/_create/{id}` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | PUT | `/{index}/_create/{id}` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/{index}/_doc` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | GET | `/_mget` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | GET | `/{index}/_mget` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/_mget` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/{index}/_mget` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | GET | `/_mtermvectors` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/_mtermvectors` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | GET | `/{index}/_mtermvectors` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/{index}/_mtermvectors` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | GET | `/{index}/_termvectors` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/{index}/_termvectors` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | GET | `/{index}/_termvectors/{id}` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/{index}/_termvectors/{id}` | `deferred` | `no canonical runtime compare owner` |
| document-and-bulk | planned | POST | `/{index}/_update/{id}` | `deferred` | `no canonical runtime compare owner` |
| snapshot-migration-interop | planned | DELETE | `/_ingest/pipeline/{id}` | `deferred` | `no canonical runtime compare owner` |
| snapshot-migration-interop | planned | GET | `/_ingest/pipeline` | `deferred` | `no canonical runtime compare owner` |
| snapshot-migration-interop | planned | GET | `/_ingest/pipeline/{id}` | `deferred` | `no canonical runtime compare owner` |
| snapshot-migration-interop | planned | PUT | `/_ingest/pipeline/{id}` | `deferred` | `no canonical runtime compare owner` |
| snapshot-migration-interop | planned | GET | `/_ingest/pipeline/{id}/_simulate` | `deferred` | `no canonical runtime compare owner` |
| snapshot-migration-interop | planned | POST | `/_ingest/pipeline/{id}/_simulate` | `deferred` | `no canonical runtime compare owner` |
| snapshot-migration-interop | planned | GET | `/_ingest/pipeline/_simulate` | `deferred` | `no canonical runtime compare owner` |
| snapshot-migration-interop | planned | POST | `/_ingest/pipeline/_simulate` | `deferred` | `no canonical runtime compare owner` |
| misc | planned | GET | `/_list/indices` | `deferred` | `no canonical runtime compare owner` |
| misc | planned | GET | `/_list/indices/{index}` | `deferred` | `no canonical runtime compare owner` |
| misc | planned | GET | `/_list` | `deferred` | `no canonical runtime compare owner` |
| misc | planned | GET | `/_list/shards` | `deferred` | `no canonical runtime compare owner` |
| misc | planned | GET | `/_list/shards/{index}` | `deferred` | `no canonical runtime compare owner` |
| search | planned | DELETE | `/_search/scroll` | `deferred` | `no canonical runtime compare owner` |
| search | planned | DELETE | `/_search/scroll/{scroll_id}` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/_count` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/_count` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/{index}/_count` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/{index}/_count` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/{index}/_search/point_in_time` | `deferred` | `no canonical runtime compare owner` |
| search | planned | DELETE | `/_search/point_in_time` | `deferred` | `no canonical runtime compare owner` |
| search | planned | DELETE | `/_search/point_in_time/_all` | `deferred` | `no canonical runtime compare owner` |
| search | planned | DELETE | `/_search/pipeline/{id}` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/{index}/_explain/{id}` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/{index}/_explain/{id}` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/_search/point_in_time/_all` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/_search/pipeline` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/_search/pipeline/{id}` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/_msearch` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/_msearch` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/{index}/_msearch` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/{index}/_msearch` | `deferred` | `no canonical runtime compare owner` |
| search | planned | PUT | `/_search/pipeline/{id}` | `deferred` | `no canonical runtime compare owner` |
| search | implemented-read | GET | `/_search` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | planned | POST | `/_search` | `deferred` | `no canonical runtime compare owner` |
| search | implemented-read | GET | `/{index}/_search` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/{index}/_search` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | planned | GET | `/_search/scroll` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/_search/scroll` | `deferred` | `no canonical runtime compare owner` |
| search | planned | GET | `/_search/scroll/{scroll_id}` | `deferred` | `no canonical runtime compare owner` |
| search | planned | POST | `/_search/scroll/{scroll_id}` | `deferred` | `no canonical runtime compare owner` |
| misc | planned | POST | `/{index}/_tier/ + targetTier` | `deferred` | `no canonical runtime compare owner` |
| misc | planned | POST | `/_tier/_cancel/{index}` | `deferred` | `no canonical runtime compare owner` |
| misc | planned | GET | `/{index}/_tier` | `deferred` | `no canonical runtime compare owner` |
| misc | planned | GET | `/_tier/all` | `deferred` | `no canonical runtime compare owner` |
| vector-and-ml | planned | POST | `String.format(Locale.ROOT, "%s/%s/{%s}", KNNPlugin.KNN_BASE_URI, CLEAR_CACHE, INDEX)` | `deferred` | `no canonical runtime compare owner` |
| vector-and-ml | planned | DELETE | `String.format(Locale.ROOT, "%s/%s/{%s}", KNNPlugin.KNN_BASE_URI, MODELS, MODEL_ID)` | `deferred` | `no canonical runtime compare owner` |
| vector-and-ml | planned | GET | `String.format(Locale.ROOT, "%s/%s/{%s}", KNNPlugin.KNN_BASE_URI, MODELS, MODEL_ID)` | `deferred` | `no canonical runtime compare owner` |
| vector-and-ml | planned | GET | `KNNPlugin.KNN_BASE_URI + "/{nodeId}/stats/"` | `deferred` | `no canonical runtime compare owner` |
| vector-and-ml | planned | GET | `KNNPlugin.KNN_BASE_URI + "/{nodeId}/stats/{stat}"` | `deferred` | `no canonical runtime compare owner` |
| vector-and-ml | planned | GET | `KNNPlugin.KNN_BASE_URI + "/stats/"` | `deferred` | `no canonical runtime compare owner` |
| vector-and-ml | planned | GET | `KNNPlugin.KNN_BASE_URI + "/stats/{stat}"` | `deferred` | `no canonical runtime compare owner` |
| vector-and-ml | planned | GET | `KNNPlugin.KNN_BASE_URI + URL_PATH` | `deferred` | `no canonical runtime compare owner` |
| vector-and-ml | planned | GET | `String.format(Locale.ROOT, "%s/%s/%s", KNNPlugin.KNN_BASE_URI, MODELS, SEARCH)` | `deferred` | `no canonical runtime compare owner` |
| vector-and-ml | planned | POST | `String.format(Locale.ROOT, "%s/%s/%s", KNNPlugin.KNN_BASE_URI, MODELS, SEARCH)` | `deferred` | `no canonical runtime compare owner` |
| vector-and-ml | planned | POST | `String.format(Locale.ROOT, "%s/%s/{%s}/_train", KNNPlugin.KNN_BASE_URI, MODELS, MODEL_ID)` | `deferred` | `no canonical runtime compare owner` |
| vector-and-ml | implemented-stateful | POST | `String.format(Locale.ROOT, "%s/%s/_train", KNNPlugin.KNN_BASE_URI, MODELS)` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
