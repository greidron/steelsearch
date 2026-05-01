# Generated Route Evidence Matrix

This file maps each source-derived REST route to its current Steelsearch
status and the canonical comparison/profile owner when one exists.

| family | status | method | path_or_expression | evidence_profile | evidence_entrypoint |
| --- | --- | --- | --- | --- | --- |
| snapshot-migration-interop | implemented-read | GET | `/_ingest/processor/grok` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| search | implemented-read | GET | `/_msearch/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/_msearch/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-read | GET | `/{index}/_msearch/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/{index}/_msearch/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-read | GET | `/_render/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/_render/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | GET | `/_render/template/{id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/_render/template/{id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-read | GET | `/_search/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/_search/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-read | GET | `/{index}/_search/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/{index}/_search/template` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| snapshot-migration-interop | implemented-read | GET | `/_scripts/painless/_context` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented-read | GET | `/_scripts/painless/_execute` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented-stateful | POST | `/_scripts/painless/_execute` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| search | implemented-stateful | GET | `/ + ENDPOINT` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/ + ENDPOINT` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | GET | `/{index}/ + ENDPOINT` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/{index}/ + ENDPOINT` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| document-and-bulk | implemented-stateful | POST | `/{index}/_delete_by_query` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/_reindex` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/_update_by_query/{taskId}/_rethrottle` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/_delete_by_query/{taskId}/_rethrottle` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/_reindex/{taskId}/_rethrottle` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/{index}/_update_by_query` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
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
| misc | implemented-read | GET | `/_field_caps` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented-stateful | POST | `/_field_caps` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented-read | GET | `/{index}/_field_caps` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented-stateful | POST | `/{index}/_field_caps` | `deferred` | `no canonical runtime compare owner` |
| root-cluster-node | implemented | GET | `/` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented | HEAD | `/` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_cluster/voting_config_exclusions` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_tasks/_cancel` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_tasks/{task_id}/_cancel` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_snapshot/{repository}/_cleanup` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | DELETE | `/_cluster/voting_config_exclusions` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | PUT | `/_snapshot/{repository}/{snapshot}/_clone/{target_snapshot}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | GET | `/_cluster/allocation/explain` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_cluster/allocation/explain` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | DELETE | `/_cluster/routing/awareness/weights` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | DELETE | `/_cluster/routing/awareness/{attribute}/weights` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/settings` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | GET | `/_cluster/routing/awareness/{attribute}/weights` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/health` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/health/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | PUT | `/_cluster/routing/awareness/{attribute}/weights` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_cluster/reroute` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | GET | `/_search_shards` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_search_shards` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | GET | `/{index}/_search_shards` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/{index}/_search_shards` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/state` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/state/{metric}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/state/{metric}/{indices}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/stats` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/stats/nodes/{nodeId}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/stats/{metric}/nodes/{nodeId}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/stats/{metric}/{index_metric}/nodes/{nodeId}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | PUT | `/_cluster/settings` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_snapshot/{repository}/{snapshot}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | PUT | `/_snapshot/{repository}/{snapshot}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | PUT | `/_cluster/decommission/awareness/{awareness_attribute_name}/{awareness_attribute_value}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | DELETE | `/_cluster/decommission/awareness` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | DELETE | `/_snapshot/{repository}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | DELETE | `/_snapshot/{repository}/{snapshot}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | DELETE | `/_scripts/{id}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/decommission/awareness/{awareness_attribute_name}/_status` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_snapshot` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | GET | `/_snapshot/{repository}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_script_context` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_script_language` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | GET | `/_snapshot/{repository}/{snapshot}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | GET | `/_scripts/{id}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_tasks/{task_id}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_tasks` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_nodes/hot_threads` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_nodes/{nodeId}/hot_threads` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_nodes` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_nodes/{nodeId}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_nodes/{nodeId}/{metrics}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_nodes/{nodeId}/info/{metrics}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_nodes/stats` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_nodes/{nodeId}/stats` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_nodes/stats/{metric}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_nodes/{nodeId}/stats/{metric}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_nodes/stats/{metric}/{index_metric}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_nodes/{nodeId}/stats/{metric}/{index_metric}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_nodes/usage` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_nodes/{nodeId}/usage` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_nodes/usage/{metric}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_nodes/{nodeId}/usage/{metric}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cluster/pending_tasks` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_filecache/prune` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_snapshot/{repository}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | PUT | `/_snapshot/{repository}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_scripts/{id}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | PUT | `/_scripts/{id}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_scripts/{id}/{context}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | PUT | `/_scripts/{id}/{context}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_nodes/reload_secure_settings` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_nodes/{nodeId}/reload_secure_settings` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_remote/info` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_remotestore/metadata/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_remotestore/metadata/{index}/{shard_id}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_remotestore/stats/{index}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_remotestore/stats/{index}/{shard_id}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_remotestore/_restore` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_snapshot/{repository}/{snapshot}/_restore` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_snapshot/{repository}/{snapshot}/{index}/_status` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_snapshot/{repository}/{snapshot}/_status` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_snapshot/{repository}/_status` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_snapshot/_status` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_snapshot/{repository}/_verify` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `_wlm/stats` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `_wlm/{nodeId}/stats` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `_wlm/stats/{workloadGroupId}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `_wlm/{nodeId}/stats/{workloadGroupId}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `_list/wlm_stats` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `_list/wlm_stats/{nodeId}/stats` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `_list/wlm_stats/stats/{workloadGroupId}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `_list/wlm_stats/{nodeId}/stats/{workloadGroupId}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | DELETE | `/_dangling/{index_uuid}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-stateful | POST | `/_dangling/{index_uuid}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_dangling` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| index-and-metadata | implemented-stateful | PUT | `/{index}/_block/{block}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_analyze` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_analyze` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/{index}/_analyze` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_analyze` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_cache/clear` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_cache/clear` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_close` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_close` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/_data_stream/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/{index}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_data_stream/_stats` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_data_stream/{name}/_stats` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | DELETE | `/_component_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | DELETE | `/_index_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | DELETE | `/_data_stream/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | DELETE | `/{index}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | DELETE | `/_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_flush` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_flush` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/{index}/_flush` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_flush` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_forcemerge` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_forcemerge` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | GET | `/_alias` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | GET | `/_aliases` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | GET | `/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | HEAD | `/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | GET | `/{index}/_alias` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | HEAD | `/{index}/_alias` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | GET | `/{index}/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | HEAD | `/{index}/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_component_template` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | GET | `/_component_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | HEAD | `/_component_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_index_template` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | GET | `/_index_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | HEAD | `/_index_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_data_stream` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | GET | `/_data_stream/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_mapping/field/{fields}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/{index}/_mapping/field/{fields}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_template` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | GET | `/_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | HEAD | `/_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | GET | `/{index}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | HEAD | `/{index}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | GET | `/{index}/ingestion/_state` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_mapping` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_mappings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | GET | `/{index}/_mapping` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | GET | `/{index}/_mappings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | GET | `/_settings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_settings/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | GET | `/{index}/_settings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/{index}/_settings/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/{index}/_setting/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | DELETE | `/{index}/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | DELETE | `/{index}/_aliases/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/{index}/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/_alias/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_aliases/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/{index}/_aliases/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_aliases/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/_aliases/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/{index}/_alias` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/{index}/_aliases` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/_alias` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_aliases` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_segments` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/{index}/_segments` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_shard_stores` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/{index}/_shard_stores` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_stats` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_stats/{metric}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/{index}/_stats` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/{index}/_stats/{metric}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_open` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_open` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/ingestion/_pause` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_component_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/_component_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_index_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/_index_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/_template/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_mapping` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/{index}/_mapping` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_mappings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/{index}/_mappings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_recovery` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/{index}/_recovery` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| document-and-bulk | implemented-read | GET | `/_refresh` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/_refresh` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-read | GET | `/{index}/_refresh` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/{index}/_refresh` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_shrink/{target}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/{index}/_shrink/{target}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_split/{target}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/{index}/_split/{target}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_clone/{target}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/{index}/_clone/{target}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_resolve/index/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/ingestion/_resume` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_rollover` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_rollover/{new_index}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_scale` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_index_template/_simulate_index/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_index_template/_simulate` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_index_template/_simulate/{name}` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_flush/synced` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_flush/synced` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/{index}/_flush/synced` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_flush/synced` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/_settings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | PUT | `/{index}/_settings` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/_upgrade` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | POST | `/{index}/_upgrade` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-read | GET | `/_upgrade` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| index-and-metadata | implemented-stateful | GET | `/{index}/_upgrade` | `index-metadata` | `tools/run-phase-a-acceptance-harness.sh --scope index-metadata` |
| search | implemented-read | GET | `/_validate/query` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/_validate/query` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-read | GET | `/{index}/_validate/query` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/{index}/_validate/query` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| root-cluster-node | implemented-read | GET | `/_cat/aliases` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/aliases/{alias}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/allocation` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat/allocation/{nodes}` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
| root-cluster-node | implemented-read | GET | `/_cat` | `root-cluster-node` | `tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` |
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
| document-and-bulk | implemented-stateful | POST | `/_bulk` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/{index}/_bulk` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | PUT | `/_bulk` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | PUT | `/{index}/_bulk` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/_bulk/stream` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | PUT | `/_bulk/stream` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/{index}/_bulk/stream` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | PUT | `/{index}/_bulk/stream` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | DELETE | `/{index}/_doc/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | GET | `/{index}/_doc/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | HEAD | `/{index}/_doc/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-read | GET | `/{index}/_source/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-read | HEAD | `/{index}/_source/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/{index}/_doc/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | PUT | `/{index}/_doc/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/{index}/_create/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | PUT | `/{index}/_create/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/{index}/_doc` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-read | GET | `/_mget` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-read | GET | `/{index}/_mget` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/_mget` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/{index}/_mget` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-read | GET | `/_mtermvectors` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/_mtermvectors` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-read | GET | `/{index}/_mtermvectors` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/{index}/_mtermvectors` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-read | GET | `/{index}/_termvectors` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/{index}/_termvectors` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-read | GET | `/{index}/_termvectors/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/{index}/_termvectors/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| document-and-bulk | implemented-stateful | POST | `/{index}/_update/{id}` | `document-write-path` | `tools/run-phase-a-acceptance-harness.sh --scope document-write-path` |
| snapshot-migration-interop | implemented-stateful | DELETE | `/_ingest/pipeline/{id}` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented-read | GET | `/_ingest/pipeline` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented-stateful | GET | `/_ingest/pipeline/{id}` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented-stateful | PUT | `/_ingest/pipeline/{id}` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented-read | GET | `/_ingest/pipeline/{id}/_simulate` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented-stateful | POST | `/_ingest/pipeline/{id}/_simulate` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented-read | GET | `/_ingest/pipeline/_simulate` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| snapshot-migration-interop | implemented-stateful | POST | `/_ingest/pipeline/_simulate` | `snapshot-migration` | `tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` |
| misc | implemented-read | GET | `/_list/indices` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented-read | GET | `/_list/indices/{index}` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented-read | GET | `/_list` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented-read | GET | `/_list/shards` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented-read | GET | `/_list/shards/{index}` | `deferred` | `no canonical runtime compare owner` |
| search | implemented-stateful | DELETE | `/_search/scroll` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | DELETE | `/_search/scroll/{scroll_id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-read | GET | `/_count` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/_count` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-read | GET | `/{index}/_count` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/{index}/_count` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/{index}/_search/point_in_time` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | DELETE | `/_search/point_in_time` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | DELETE | `/_search/point_in_time/_all` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | DELETE | `/_search/pipeline/{id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-read | GET | `/{index}/_explain/{id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/{index}/_explain/{id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | GET | `/_search/point_in_time/_all` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-read | GET | `/_search/pipeline` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | GET | `/_search/pipeline/{id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-read | GET | `/_msearch` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/_msearch` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-read | GET | `/{index}/_msearch` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/{index}/_msearch` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | PUT | `/_search/pipeline/{id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-read | GET | `/_search` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/_search` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-read | GET | `/{index}/_search` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/{index}/_search` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | GET | `/_search/scroll` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/_search/scroll` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-read | GET | `/_search/scroll/{scroll_id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| search | implemented-stateful | POST | `/_search/scroll/{scroll_id}` | `search` | `tools/run-phase-a-acceptance-harness.sh --scope search` |
| misc | implemented-stateful | POST | `/{index}/_tier/ + targetTier` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented-stateful | POST | `/_tier/_cancel/{index}` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented-read | GET | `/{index}/_tier` | `deferred` | `no canonical runtime compare owner` |
| misc | implemented-read | GET | `/_tier/all` | `deferred` | `no canonical runtime compare owner` |
| vector-and-ml | implemented-stateful | POST | `String.format(Locale.ROOT, "%s/%s/{%s}", KNNPlugin.KNN_BASE_URI, CLEAR_CACHE, INDEX)` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented-stateful | DELETE | `String.format(Locale.ROOT, "%s/%s/{%s}", KNNPlugin.KNN_BASE_URI, MODELS, MODEL_ID)` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented-stateful | GET | `String.format(Locale.ROOT, "%s/%s/{%s}", KNNPlugin.KNN_BASE_URI, MODELS, MODEL_ID)` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented-read | GET | `KNNPlugin.KNN_BASE_URI + "/{nodeId}/stats/"` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented-read | GET | `KNNPlugin.KNN_BASE_URI + "/{nodeId}/stats/{stat}"` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented-read | GET | `KNNPlugin.KNN_BASE_URI + "/stats/"` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented-read | GET | `KNNPlugin.KNN_BASE_URI + "/stats/{stat}"` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented-read | GET | `KNNPlugin.KNN_BASE_URI + URL_PATH` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented-stateful | GET | `String.format(Locale.ROOT, "%s/%s/%s", KNNPlugin.KNN_BASE_URI, MODELS, SEARCH)` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented-stateful | POST | `String.format(Locale.ROOT, "%s/%s/%s", KNNPlugin.KNN_BASE_URI, MODELS, SEARCH)` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented-stateful | POST | `String.format(Locale.ROOT, "%s/%s/{%s}/_train", KNNPlugin.KNN_BASE_URI, MODELS, MODEL_ID)` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
| vector-and-ml | implemented-stateful | POST | `String.format(Locale.ROOT, "%s/%s/_train", KNNPlugin.KNN_BASE_URI, MODELS)` | `vector-ml` | `tools/run-phase-a-acceptance-harness.sh --scope vector-ml` |
