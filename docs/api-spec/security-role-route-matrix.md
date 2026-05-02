# Security Role Route Matrix

This document fixes the minimum-role target for the secure standalone
compatibility harness. It is a planning and evidence matrix, not a claim that
the current runtime already enforces every row below.

## Reading Rules

- `reader` means read-only cluster/index access sufficient for search and
  metadata inspection.
- `writer` means document mutation rights without broad cluster-admin powers.
- `admin` means cluster/configuration/snapshot level access.
- `high-risk` marks route families that must be tracked separately in
  `tasks.md` because mistakes here can expose cluster-wide mutation or data
  loss.
- `Required action / privilege` is the canonical secure-standalone authz label
  for probe planning. It may later map onto one or more concrete OpenSearch
  privilege strings, but the label itself is the current source of truth for
  fixture design.

## Reader Role

| Route family | Representative routes | Minimum role | Required action / privilege | Why |
| --- | --- | --- | --- | --- |
| Root and cluster read | `GET /`, `GET /_cluster/health` | `reader` | `cluster:monitor/main`, `cluster:monitor/health` | Basic authenticated health and identity checks |
| Search read | `GET|POST /_search`, `GET|POST /{index}/_search`, `/_msearch`, `/_search/template` | `reader` | `indices:data/read/search*` | Query execution without mutation |
| Readback and explain | `GET /{index}/_doc/{id}`, `HEAD /{index}/_doc/{id}`, `GET|POST /{index}/_explain/{id}` | `reader` | `indices:data/read/get`, `indices:data/read/explain` | Per-document read and explanation |
| Metadata read | `GET /_alias*`, `GET /_field_caps`, `GET /{index}/_mapping`, `GET /{index}/_settings` | `reader` | `indices:admin/aliases/get`, `indices:admin/field_caps`, `indices:admin/mappings/get`, `indices:admin/settings/get` | Index metadata inspection |
| Session read | `GET /_search/scroll`, `GET /_search/point_in_time/_all` | `reader` | `indices:data/read/scroll`, `indices:data/read/point_in_time/read` | Read-only session lifecycle inspection |

## Writer Role

| Route family | Representative routes | Minimum role | Required action / privilege | Why |
| --- | --- | --- | --- | --- |
| Single-document write | `POST /{index}/_doc`, `PUT /{index}/_doc/{id}`, `POST /{index}/_create/{id}`, `POST /{index}/_update/{id}` | `writer` | `indices:data/write/index`, `indices:data/write/create`, `indices:data/write/update` | Direct document mutation |
| Bulk and batch write | `POST /_bulk`, `POST /{index}/_bulk`, `POST /_reindex` | `writer` | `indices:data/write/bulk`, `indices:data/write/reindex` | Multi-document mutation surface |
| Query-driven mutation | `POST /{index}/_delete_by_query`, `POST /{index}/_update_by_query` | `writer` | `indices:data/write/delete/byquery`, `indices:data/write/update/byquery` | Mutation via query selection |
| Lightweight maintenance | `POST /_refresh`, `POST /_flush`, `POST /_cache/clear`, `POST /_forcemerge` | `writer` | `indices:admin/refresh`, `indices:admin/flush`, `indices:admin/cache/clear`, `indices:admin/forcemerge` | Index-local maintenance without cluster-admin configuration |

## Admin Role

| Route family | Representative routes | Minimum role | Required action / privilege | Risk | Why |
| --- | --- | --- | --- | --- | --- |
| Cluster settings | `GET|PUT /_cluster/settings`, `GET /_cluster/state`, `POST /_cluster/reroute` | `admin` | `cluster:admin/settings/*`, `cluster:monitor/state`, `cluster:admin/reroute` | `high-risk` | Cluster-wide state mutation and visibility |
| Snapshot and repository | `PUT|GET|DELETE /_snapshot/{repo}`, `POST /_snapshot/{repo}/_cleanup`, `POST /_snapshot/{repo}/{snapshot}/_restore` | `admin` | `cluster:admin/repository/*`, `cluster:admin/snapshot/*` | `high-risk` | Backup, restore, and repository ownership |
| Index settings and templates | `PUT /{index}/_settings`, `PUT /_template/*`, `PUT /_index_template/*`, `PUT /_component_template/*` | `admin` | `indices:admin/settings/update`, `indices:admin/template/*`, `cluster:admin/component_template/*`, `cluster:admin/index_template/*` | `high-risk` | Persistent metadata mutation |
| Alias and data stream mutation | `PUT|POST|DELETE /_alias*`, `PUT|DELETE /_data_stream/*` | `admin` | `indices:admin/aliases*`, `indices:admin/data_stream/*` | medium | Namespace and routing indirection mutation |
| Scripts and ingest pipeline | `PUT|DELETE /_scripts/*`, `PUT|DELETE /_ingest/pipeline/*`, `POST /_scripts/painless/_execute` | `admin` | `cluster:admin/script/*`, `cluster:admin/ingest/pipeline/*` | medium | Shared execution/configuration surface |
| Task and tier control | `POST /_tasks/_cancel*`, `POST /_tasks/{id}/_rethrottle`, `POST /_tier/_cancel/*`, `POST /{index}/_tier/*` | `admin` | `cluster:admin/tasks/*`, `indices:admin/tier/*` | medium | Operational control plane |

## High-Risk Route Families To Track Separately

These route groups need explicit success, forbidden, and overbroad-access
probes even after the minimum-role matrix exists:

- `/_bulk`
- `/_search`
- `/{index}/_settings`
- `/_snapshot/*`
- `/_cluster/*`

## Immediate Probe Follow-up

The next security/authz probe batches should use this matrix as the source of
truth:

1. `reader` success on root/index read plus `403` on document write.
2. `writer` success on document write plus `403` on admin routes.
3. `admin` success on one cluster route and one snapshot route.
4. Overbroad access checks for the high-risk families listed above.

## Privilege Naming Notes

- These labels are intentionally stable for fixture design even where the final
  security implementation may compress them into broader built-in roles.
- If a route family later resolves to a different concrete OpenSearch privilege
  string, update this document and the corresponding fixture case together.
