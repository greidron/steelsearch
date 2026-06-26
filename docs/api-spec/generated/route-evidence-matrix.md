# Generated Route Evidence Matrix

This file maps each source-derived REST route to its current Steelsearch
status and the canonical comparison/profile owner when one exists.

| family | status | method | path_or_expression | evidence_profile | evidence_entrypoint |
| --- | --- | --- | --- | --- | --- |
| snapshot-migration-interop | implemented | GET | `/_ingest/processor/grok` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| search | implemented | GET | `/_msearch/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/_msearch/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/{index}/_msearch/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/{index}/_msearch/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/_render/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/_render/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/_render/template/{id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/_render/template/{id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/_search/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/_search/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/{index}/_search/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/{index}/_search/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| snapshot-migration-interop | implemented | GET | `/_scripts/painless/_context` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented | GET | `/_scripts/painless/_execute` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented | POST | `/_scripts/painless/_execute` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| search | implemented | GET | `/ + ENDPOINT` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/ + ENDPOINT` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/{index}/ + ENDPOINT` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/{index}/ + ENDPOINT` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| document-and-bulk | implemented | POST | `/{index}/_delete_by_query` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/_reindex` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/_update_by_query/{taskId}/_rethrottle` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/_delete_by_query/{taskId}/_rethrottle` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/_reindex/{taskId}/_rethrottle` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/{index}/_update_by_query` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
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
| misc | implemented | GET | `/_field_caps` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented | POST | `/_field_caps` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented | GET | `/{index}/_field_caps` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented | POST | `/{index}/_field_caps` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented | GET | `/` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | HEAD | `/` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_cluster/voting_config_exclusions` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_tasks/_cancel` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_tasks/{task_id}/_cancel` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_snapshot/{repository}/_cleanup` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | DELETE | `/_cluster/voting_config_exclusions` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | PUT | `/_snapshot/{repository}/{snapshot}/_clone/{target_snapshot}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cluster/allocation/explain` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_cluster/allocation/explain` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | DELETE | `/_cluster/routing/awareness/weights` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | DELETE | `/_cluster/routing/awareness/{attribute}/weights` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cluster/settings` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cluster/routing/awareness/{attribute}/weights` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cluster/health` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cluster/health/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | PUT | `/_cluster/routing/awareness/{attribute}/weights` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_cluster/reroute` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_search_shards` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_search_shards` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/{index}/_search_shards` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/{index}/_search_shards` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cluster/state` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cluster/state/{metric}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cluster/state/{metric}/{indices}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cluster/stats` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cluster/stats/nodes/{nodeId}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cluster/stats/{metric}/nodes/{nodeId}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cluster/stats/{metric}/{index_metric}/nodes/{nodeId}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | PUT | `/_cluster/settings` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_snapshot/{repository}/{snapshot}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | PUT | `/_snapshot/{repository}/{snapshot}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | PUT | `/_cluster/decommission/awareness/{awareness_attribute_name}/{awareness_attribute_value}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | DELETE | `/_cluster/decommission/awareness` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | DELETE | `/_snapshot/{repository}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | DELETE | `/_snapshot/{repository}/{snapshot}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | DELETE | `/_scripts/{id}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cluster/decommission/awareness/{awareness_attribute_name}/_status` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_snapshot` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_snapshot/{repository}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_script_context` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_script_language` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_snapshot/{repository}/{snapshot}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_scripts/{id}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_tasks/{task_id}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_tasks` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_nodes/hot_threads` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_nodes/{nodeId}/hot_threads` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_nodes` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_nodes/{nodeId}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_nodes/{nodeId}/{metrics}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_nodes/{nodeId}/info/{metrics}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_nodes/stats` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_nodes/{nodeId}/stats` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_nodes/stats/{metric}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_nodes/{nodeId}/stats/{metric}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_nodes/stats/{metric}/{index_metric}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_nodes/{nodeId}/stats/{metric}/{index_metric}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_nodes/usage` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_nodes/{nodeId}/usage` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_nodes/usage/{metric}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_nodes/{nodeId}/usage/{metric}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cluster/pending_tasks` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_filecache/prune` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_snapshot/{repository}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | PUT | `/_snapshot/{repository}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_scripts/{id}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | PUT | `/_scripts/{id}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_scripts/{id}/{context}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | PUT | `/_scripts/{id}/{context}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_nodes/reload_secure_settings` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_nodes/{nodeId}/reload_secure_settings` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_remote/info` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_remotestore/metadata/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_remotestore/metadata/{index}/{shard_id}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_remotestore/stats/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_remotestore/stats/{index}/{shard_id}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_remotestore/_restore` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_snapshot/{repository}/{snapshot}/_restore` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_snapshot/{repository}/{snapshot}/{index}/_status` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_snapshot/{repository}/{snapshot}/_status` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_snapshot/{repository}/_status` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_snapshot/_status` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_snapshot/{repository}/_verify` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `_wlm/stats` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `_wlm/{nodeId}/stats` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `_wlm/stats/{workloadGroupId}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `_wlm/{nodeId}/stats/{workloadGroupId}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `_list/wlm_stats` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `_list/wlm_stats/{nodeId}/stats` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `_list/wlm_stats/stats/{workloadGroupId}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `_list/wlm_stats/{nodeId}/stats/{workloadGroupId}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | DELETE | `/_dangling/{index_uuid}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | POST | `/_dangling/{index_uuid}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_dangling` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| index-and-metadata | implemented | PUT | `/{index}/_block/{block}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_analyze` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_analyze` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_analyze` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_analyze` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_cache/clear` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_cache/clear` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_close` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_close` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/_data_stream/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/{index}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_data_stream/_stats` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_data_stream/{name}/_stats` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | DELETE | `/_component_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | DELETE | `/_index_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | DELETE | `/_data_stream/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | DELETE | `/{index}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | DELETE | `/_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_flush` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_flush` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_flush` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_flush` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_forcemerge` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_forcemerge` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_alias` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_aliases` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | HEAD | `/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_alias` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | HEAD | `/{index}/_alias` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | HEAD | `/{index}/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_component_template` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_component_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | HEAD | `/_component_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_index_template` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_index_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | HEAD | `/_index_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_data_stream` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_data_stream/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_mapping/field/{fields}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_mapping/field/{fields}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_template` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | HEAD | `/_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | HEAD | `/{index}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/ingestion/_state` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_mapping` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_mappings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_mapping` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_mappings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_settings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_settings/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_settings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_settings/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_setting/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | DELETE | `/{index}/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | DELETE | `/{index}/_aliases/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/{index}/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_aliases/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/{index}/_aliases/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_aliases/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/_aliases/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/{index}/_alias` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/{index}/_aliases` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/_alias` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_aliases` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_segments` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_segments` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_shard_stores` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_shard_stores` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_stats` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_stats/{metric}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_stats` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_stats/{metric}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_open` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_open` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/ingestion/_pause` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_component_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/_component_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_index_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/_index_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_mapping` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/{index}/_mapping` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_mappings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/{index}/_mappings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_recovery` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_recovery` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| document-and-bulk | implemented | GET | `/_refresh` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/_refresh` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | GET | `/{index}/_refresh` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/{index}/_refresh` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| index-and-metadata | implemented | POST | `/{index}/_shrink/{target}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/{index}/_shrink/{target}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_split/{target}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/{index}/_split/{target}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_clone/{target}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/{index}/_clone/{target}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_resolve/index/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/ingestion/_resume` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_rollover` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_rollover/{new_index}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_scale` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_index_template/_simulate_index/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_index_template/_simulate` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_index_template/_simulate/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_flush/synced` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_flush/synced` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_flush/synced` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_flush/synced` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/_settings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | PUT | `/{index}/_settings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/_upgrade` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | POST | `/{index}/_upgrade` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/_upgrade` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented | GET | `/{index}/_upgrade` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| search | implemented | GET | `/_validate/query` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/_validate/query` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/{index}/_validate/query` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/{index}/_validate/query` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| root-cluster-node | implemented | GET | `/_cat/aliases` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/aliases/{alias}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/allocation` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/allocation/{nodes}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/recovery` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/recovery/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/count` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/count/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/fielddata` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/fielddata/{fields}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/health` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/indices` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/indices/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/nodeattrs` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/nodes` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/pending_tasks` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/pit_segments` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/pit_segments/_all` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/plugins` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/repositories` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/segments` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/segments/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/shards` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/shards/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/snapshots` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/snapshots/{repository}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/tasks` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/templates` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/templates/{name}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/thread_pool` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | GET | `/_cat/thread_pool/{thread_pool_patterns}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| document-and-bulk | implemented | POST | `/_bulk` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/{index}/_bulk` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | PUT | `/_bulk` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | PUT | `/{index}/_bulk` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/_bulk/stream` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | PUT | `/_bulk/stream` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/{index}/_bulk/stream` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | PUT | `/{index}/_bulk/stream` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | DELETE | `/{index}/_doc/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | GET | `/{index}/_doc/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | HEAD | `/{index}/_doc/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | GET | `/{index}/_source/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | HEAD | `/{index}/_source/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/{index}/_doc/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | PUT | `/{index}/_doc/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/{index}/_create/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | PUT | `/{index}/_create/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/{index}/_doc` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | GET | `/_mget` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | GET | `/{index}/_mget` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/_mget` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/{index}/_mget` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | GET | `/_mtermvectors` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/_mtermvectors` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | GET | `/{index}/_mtermvectors` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/{index}/_mtermvectors` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | GET | `/{index}/_termvectors` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/{index}/_termvectors` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | GET | `/{index}/_termvectors/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/{index}/_termvectors/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented | POST | `/{index}/_update/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| snapshot-migration-interop | implemented | DELETE | `/_ingest/pipeline/{id}` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented | GET | `/_ingest/pipeline` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented | GET | `/_ingest/pipeline/{id}` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented | PUT | `/_ingest/pipeline/{id}` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented | GET | `/_ingest/pipeline/{id}/_simulate` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented | POST | `/_ingest/pipeline/{id}/_simulate` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented | GET | `/_ingest/pipeline/_simulate` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented | POST | `/_ingest/pipeline/_simulate` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| misc | implemented | GET | `/_list/indices` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented | GET | `/_list/indices/{index}` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented | GET | `/_list` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented | GET | `/_list/shards` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented | GET | `/_list/shards/{index}` | `deferred` | `no canonical runtime compare owner` |
| search | implemented | DELETE | `/_search/scroll` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | DELETE | `/_search/scroll/{scroll_id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/_count` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/_count` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/{index}/_count` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/{index}/_count` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/{index}/_search/point_in_time` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | DELETE | `/_search/point_in_time` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | DELETE | `/_search/point_in_time/_all` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | DELETE | `/_search/pipeline/{id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/{index}/_explain/{id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/{index}/_explain/{id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/_search/point_in_time/_all` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/_search/pipeline` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/_search/pipeline/{id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/_msearch` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/_msearch` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/{index}/_msearch` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/{index}/_msearch` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | PUT | `/_search/pipeline/{id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/_search` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/_search` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/{index}/_search` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/{index}/_search` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/_search/scroll` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/_search/scroll` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | GET | `/_search/scroll/{scroll_id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented | POST | `/_search/scroll/{scroll_id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| misc | implemented | POST | `/{index}/_tier/ + targetTier` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented | POST | `/_tier/_cancel/{index}` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented | GET | `/{index}/_tier` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented | GET | `/_tier/all` | `deferred` | `no canonical runtime compare owner` |
| vector-and-ml | implemented | POST | `String.format(Locale.ROOT, "%s/%s/{%s}", KNNPlugin.KNN_BASE_URI, CLEAR_CACHE, INDEX)` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented | DELETE | `String.format(Locale.ROOT, "%s/%s/{%s}", KNNPlugin.KNN_BASE_URI, MODELS, MODEL_ID)` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented | GET | `String.format(Locale.ROOT, "%s/%s/{%s}", KNNPlugin.KNN_BASE_URI, MODELS, MODEL_ID)` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented | GET | `KNNPlugin.KNN_BASE_URI + "/{nodeId}/stats/"` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented | GET | `KNNPlugin.KNN_BASE_URI + "/{nodeId}/stats/{stat}"` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented | GET | `KNNPlugin.KNN_BASE_URI + "/stats/"` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented | GET | `KNNPlugin.KNN_BASE_URI + "/stats/{stat}"` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented | GET | `KNNPlugin.KNN_BASE_URI + URL_PATH` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented | GET | `String.format(Locale.ROOT, "%s/%s/%s", KNNPlugin.KNN_BASE_URI, MODELS, SEARCH)` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented | POST | `String.format(Locale.ROOT, "%s/%s/%s", KNNPlugin.KNN_BASE_URI, MODELS, SEARCH)` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented | POST | `String.format(Locale.ROOT, "%s/%s/{%s}/_train", KNNPlugin.KNN_BASE_URI, MODELS, MODEL_ID)` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented | POST | `String.format(Locale.ROOT, "%s/%s/_train", KNNPlugin.KNN_BASE_URI, MODELS)` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
