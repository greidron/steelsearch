# Runtime Route Ledger

This file records runtime-backed classification for the `planned` and `stubbed` REST inventory in `route-evidence-matrix.md`.

Base URL: `http://127.0.0.1:19200`

## Summary

| runtime_status | count |
| --- | ---: |
| implemented-read | 114 |
| missing-route | 70 |
| requires-stateful-probe | 170 |
| unprobeable-expression | 19 |

## By family

| family | implemented-read | missing-route | requires-stateful-probe | unprobeable-expression |
| --- | ---: | ---: | ---: | ---: |
| document-and-bulk | 3 | 9 | 29 | 0 |
| index-and-metadata | 28 | 26 | 64 | 0 |
| misc | 0 | 9 | 5 | 0 |
| root-cluster-node | 81 | 1 | 36 | 10 |
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
| root-cluster-node | GET | `/_snapshot/{repository}/{snapshot}/{index}/_status` | `/_snapshot/repo-compat/snap-compat/logs-compat/_status` | planned |
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
