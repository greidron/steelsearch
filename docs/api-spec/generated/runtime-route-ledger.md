# Runtime Route Ledger

This file records runtime-backed classification for the `planned` and `stubbed` REST inventory in `route-evidence-matrix.md`.

Base URL: `http://127.0.0.1:19200`

## Summary

| runtime_status | count |
| --- | ---: |
| implemented-read | 58 |
| missing-route | 124 |
| requires-stateful-probe | 170 |
| unprobeable-expression | 19 |

## By family

| family | implemented-read | missing-route | requires-stateful-probe | unprobeable-expression |
| --- | ---: | ---: | ---: | ---: |
| document-and-bulk | 3 | 9 | 29 | 0 |
| index-and-metadata | 28 | 26 | 64 | 0 |
| misc | 0 | 9 | 5 | 0 |
| root-cluster-node | 25 | 55 | 36 | 10 |
| search | 2 | 18 | 26 | 2 |
| snapshot-migration-interop | 0 | 7 | 5 | 0 |
| vector-and-ml | 0 | 0 | 5 | 7 |

## Missing safe read/head routes

| family | method | path | concrete_path | previous_status |
| --- | --- | --- | --- | --- |
| snapshot-migration-interop | GET | `/_ingest/processor/grok` | `/_ingest/processor/grok` | planned |
| search | GET | `/_msearch/template` | `/_msearch/template` | planned |
| search | GET | `/{index}/_msearch/template` | `/logs-compat/_msearch/template` | planned |
| search | GET | `/_render/template` | `/_render/template` | planned |
| search | GET | `/_render/template/{id}` | `/_render/template/doc-1` | planned |
| search | GET | `/_search/template` | `/_search/template` | planned |
| search | GET | `/{index}/_search/template` | `/logs-compat/_search/template` | planned |
| snapshot-migration-interop | GET | `/_scripts/painless/_context` | `/_scripts/painless/_context` | planned |
| snapshot-migration-interop | GET | `/_scripts/painless/_execute` | `/_scripts/painless/_execute` | planned |
| misc | GET | `/_field_caps` | `/_field_caps` | planned |
| misc | GET | `/{index}/_field_caps` | `/logs-compat/_field_caps` | planned |
| root-cluster-node | GET | `/_cluster/routing/awareness/{attribute}/weights` | `/_cluster/routing/awareness/zone/weights` | planned |
| root-cluster-node | GET | `/_search_shards` | `/_search_shards` | planned |
| root-cluster-node | GET | `/{index}/_search_shards` | `/logs-compat/_search_shards` | planned |
| root-cluster-node | GET | `/_cluster/stats/nodes/{nodeId}` | `/_cluster/stats/nodes/steelsearch-dev-node` | planned |
| root-cluster-node | GET | `/_cluster/stats/{metric}/nodes/{nodeId}` | `/_cluster/stats/metadata/nodes/steelsearch-dev-node` | planned |
| root-cluster-node | GET | `/_cluster/stats/{metric}/{index_metric}/nodes/{nodeId}` | `/_cluster/stats/metadata/docs/nodes/steelsearch-dev-node` | planned |
| root-cluster-node | GET | `/_cluster/decommission/awareness/{awareness_attribute_name}/_status` | `/_cluster/decommission/awareness/zone/_status` | planned |
| root-cluster-node | GET | `/_script_context` | `/_script_context` | planned |
| root-cluster-node | GET | `/_script_language` | `/_script_language` | planned |
| root-cluster-node | GET | `/_scripts/{id}` | `/_scripts/doc-1` | planned |
| root-cluster-node | GET | `/_nodes/hot_threads` | `/_nodes/hot_threads` | planned |
| root-cluster-node | GET | `/_nodes/{nodeId}/hot_threads` | `/_nodes/steelsearch-dev-node/hot_threads` | planned |
| root-cluster-node | GET | `/_nodes` | `/_nodes` | planned |
| root-cluster-node | GET | `/_nodes/{nodeId}` | `/_nodes/steelsearch-dev-node` | planned |
| root-cluster-node | GET | `/_nodes/{nodeId}/{metrics}` | `/_nodes/steelsearch-dev-node/http` | planned |
| root-cluster-node | GET | `/_nodes/{nodeId}/info/{metrics}` | `/_nodes/steelsearch-dev-node/info/http` | planned |
| root-cluster-node | GET | `/_nodes/{nodeId}/stats` | `/_nodes/steelsearch-dev-node/stats` | planned |
| root-cluster-node | GET | `/_nodes/stats/{metric}` | `/_nodes/stats/metadata` | planned |
| root-cluster-node | GET | `/_nodes/{nodeId}/stats/{metric}` | `/_nodes/steelsearch-dev-node/stats/metadata` | planned |
| root-cluster-node | GET | `/_nodes/stats/{metric}/{index_metric}` | `/_nodes/stats/metadata/docs` | planned |
| root-cluster-node | GET | `/_nodes/{nodeId}/stats/{metric}/{index_metric}` | `/_nodes/steelsearch-dev-node/stats/metadata/docs` | planned |
| root-cluster-node | GET | `/_nodes/usage` | `/_nodes/usage` | planned |
| root-cluster-node | GET | `/_nodes/{nodeId}/usage` | `/_nodes/steelsearch-dev-node/usage` | planned |
| root-cluster-node | GET | `/_nodes/usage/{metric}` | `/_nodes/usage/metadata` | planned |
| root-cluster-node | GET | `/_nodes/{nodeId}/usage/{metric}` | `/_nodes/steelsearch-dev-node/usage/metadata` | planned |
| root-cluster-node | GET | `/_remote/info` | `/_remote/info` | planned |
| root-cluster-node | GET | `/_remotestore/metadata/{index}` | `/_remotestore/metadata/logs-compat` | planned |
| root-cluster-node | GET | `/_remotestore/stats/{index}` | `/_remotestore/stats/logs-compat` | planned |
| root-cluster-node | GET | `/_snapshot/{repository}/{snapshot}/{index}/_status` | `/_snapshot/repo-compat/snap-compat/logs-compat/_status` | planned |
| root-cluster-node | GET | `/_dangling` | `/_dangling` | planned |
| index-and-metadata | GET | `/_analyze` | `/_analyze` | planned |
| index-and-metadata | GET | `/{index}/_analyze` | `/logs-compat/_analyze` | planned |
| index-and-metadata | GET | `/_flush` | `/_flush` | planned |
| index-and-metadata | GET | `/{index}/_flush` | `/logs-compat/_flush` | planned |
| index-and-metadata | GET | `/_mapping/field/{fields}` | `/_mapping/field/message` | planned |
| index-and-metadata | GET | `/{index}/_mapping/field/{fields}` | `/logs-compat/_mapping/field/message` | planned |
| index-and-metadata | GET | `/{index}/ingestion/_state` | `/logs-compat/ingestion/_state` | planned |
| index-and-metadata | GET | `/_mappings` | `/_mappings` | planned |
| index-and-metadata | GET | `/{index}/_mappings` | `/logs-compat/_mappings` | planned |
| index-and-metadata | GET | `/_settings/{name}` | `/_settings/logs-read` | planned |
| index-and-metadata | GET | `/{index}/_settings/{name}` | `/logs-compat/_settings/logs-read` | planned |
| index-and-metadata | GET | `/{index}/_setting/{name}` | `/logs-compat/_setting/logs-read` | planned |
| index-and-metadata | GET | `/_segments` | `/_segments` | planned |
| index-and-metadata | GET | `/{index}/_segments` | `/logs-compat/_segments` | planned |
| index-and-metadata | GET | `/_shard_stores` | `/_shard_stores` | planned |
| index-and-metadata | GET | `/{index}/_shard_stores` | `/logs-compat/_shard_stores` | planned |
| index-and-metadata | GET | `/_stats/{metric}` | `/_stats/metadata` | planned |
| index-and-metadata | GET | `/{index}/_stats` | `/logs-compat/_stats` | planned |
| index-and-metadata | GET | `/{index}/_stats/{metric}` | `/logs-compat/_stats/metadata` | planned |
| index-and-metadata | GET | `/_recovery` | `/_recovery` | planned |
| index-and-metadata | GET | `/{index}/_recovery` | `/logs-compat/_recovery` | planned |
| document-and-bulk | GET | `/_refresh` | `/_refresh` | planned |
| document-and-bulk | GET | `/{index}/_refresh` | `/logs-compat/_refresh` | planned |
| index-and-metadata | GET | `/_resolve/index/{name}` | `/_resolve/index/logs-read` | planned |
| index-and-metadata | GET | `/_flush/synced` | `/_flush/synced` | planned |
| index-and-metadata | GET | `/{index}/_flush/synced` | `/logs-compat/_flush/synced` | planned |
| index-and-metadata | GET | `/_upgrade` | `/_upgrade` | planned |
| index-and-metadata | GET | `/{index}/_upgrade` | `/logs-compat/_upgrade` | planned |
| search | GET | `/_validate/query` | `/_validate/query` | planned |
| search | GET | `/{index}/_validate/query` | `/logs-compat/_validate/query` | planned |
| root-cluster-node | GET | `/_cat/allocation` | `/_cat/allocation` | planned |
| root-cluster-node | GET | `/_cat/allocation/{nodes}` | `/_cat/allocation/steelsearch-dev-node` | planned |
| root-cluster-node | GET | `/_cat` | `/_cat` | planned |
| root-cluster-node | GET | `/_cat/recovery` | `/_cat/recovery` | planned |
| root-cluster-node | GET | `/_cat/recovery/{index}` | `/_cat/recovery/logs-compat` | planned |
| root-cluster-node | GET | `/_cat/count/{index}` | `/_cat/count/logs-compat` | planned |
| root-cluster-node | GET | `/_cat/fielddata` | `/_cat/fielddata` | planned |
| root-cluster-node | GET | `/_cat/fielddata/{fields}` | `/_cat/fielddata/message` | planned |
| root-cluster-node | GET | `/_cat/indices/{index}` | `/_cat/indices/logs-compat` | planned |
| root-cluster-node | GET | `/_cat/nodeattrs` | `/_cat/nodeattrs` | planned |
| root-cluster-node | GET | `/_cat/pending_tasks` | `/_cat/pending_tasks` | planned |
| root-cluster-node | GET | `/_cat/pit_segments` | `/_cat/pit_segments` | planned |
| root-cluster-node | GET | `/_cat/pit_segments/_all` | `/_cat/pit_segments/_all` | planned |
| root-cluster-node | GET | `/_cat/repositories` | `/_cat/repositories` | planned |
| root-cluster-node | GET | `/_cat/segments` | `/_cat/segments` | planned |
| root-cluster-node | GET | `/_cat/segments/{index}` | `/_cat/segments/logs-compat` | planned |
| root-cluster-node | GET | `/_cat/shards` | `/_cat/shards` | planned |
| root-cluster-node | GET | `/_cat/shards/{index}` | `/_cat/shards/logs-compat` | planned |
| root-cluster-node | GET | `/_cat/snapshots` | `/_cat/snapshots` | planned |
| root-cluster-node | GET | `/_cat/snapshots/{repository}` | `/_cat/snapshots/repo-compat` | planned |
| root-cluster-node | GET | `/_cat/tasks` | `/_cat/tasks` | planned |
| root-cluster-node | GET | `/_cat/templates` | `/_cat/templates` | planned |
| root-cluster-node | GET | `/_cat/templates/{name}` | `/_cat/templates/logs-read` | planned |
| root-cluster-node | GET | `/_cat/thread_pool` | `/_cat/thread_pool` | planned |
| root-cluster-node | GET | `/_cat/thread_pool/{thread_pool_patterns}` | `/_cat/thread_pool/search` | planned |
| document-and-bulk | GET | `/{index}/_source/{id}` | `/logs-compat/_source/doc-1` | planned |
| document-and-bulk | GET | `/_mget` | `/_mget` | planned |
| document-and-bulk | GET | `/{index}/_mget` | `/logs-compat/_mget` | planned |
| document-and-bulk | GET | `/_mtermvectors` | `/_mtermvectors` | planned |
| document-and-bulk | GET | `/{index}/_mtermvectors` | `/logs-compat/_mtermvectors` | planned |
| document-and-bulk | GET | `/{index}/_termvectors` | `/logs-compat/_termvectors` | planned |
| document-and-bulk | GET | `/{index}/_termvectors/{id}` | `/logs-compat/_termvectors/doc-1` | planned |
| snapshot-migration-interop | GET | `/_ingest/pipeline` | `/_ingest/pipeline` | planned |
| snapshot-migration-interop | GET | `/_ingest/pipeline/{id}` | `/_ingest/pipeline/doc-1` | planned |
| snapshot-migration-interop | GET | `/_ingest/pipeline/{id}/_simulate` | `/_ingest/pipeline/doc-1/_simulate` | planned |
| snapshot-migration-interop | GET | `/_ingest/pipeline/_simulate` | `/_ingest/pipeline/_simulate` | planned |
| misc | GET | `/_list/indices` | `/_list/indices` | planned |
| misc | GET | `/_list/indices/{index}` | `/_list/indices/logs-compat` | planned |
| misc | GET | `/_list` | `/_list` | planned |
| misc | GET | `/_list/shards` | `/_list/shards` | planned |
| misc | GET | `/_list/shards/{index}` | `/_list/shards/logs-compat` | planned |
| search | GET | `/_count` | `/_count` | planned |
| search | GET | `/{index}/_count` | `/logs-compat/_count` | planned |
| search | GET | `/{index}/_explain/{id}` | `/logs-compat/_explain/doc-1` | planned |
| search | GET | `/_search/point_in_time/_all` | `/_search/point_in_time/_all` | planned |
| search | GET | `/_search/pipeline` | `/_search/pipeline` | planned |
| search | GET | `/_search/pipeline/{id}` | `/_search/pipeline/doc-1` | planned |
| search | GET | `/_msearch` | `/_msearch` | planned |
| search | GET | `/{index}/_msearch` | `/logs-compat/_msearch` | planned |
| search | GET | `/_search/scroll` | `/_search/scroll` | planned |
| search | GET | `/_search/scroll/{scroll_id}` | `/_search/scroll/scroll-1` | planned |
| misc | GET | `/{index}/_tier` | `/logs-compat/_tier` | planned |
| misc | GET | `/_tier/all` | `/_tier/all` | planned |
