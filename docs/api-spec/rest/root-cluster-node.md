# Root, Cluster, And Node REST Spec

This document covers:

- root identity routes;
- cluster health/state/settings routes;
- node stats and diagnostics;
- task and cat-style operator routes.

## Semantic Summary

These APIs tell a client or operator what node they reached, what cluster state
looks like, and how the cluster is behaving operationally. In OpenSearch they
are often used by:

- health checks and bootstrap probes;
- cluster managers and orchestration systems;
- monitoring and dashboards;
- operator debugging and maintenance.

## Current Steelsearch Position

- `GET /` and `HEAD /` exist and are the closest to parity.
- Cluster health/state/settings and selected stats routes exist in development
  form, but not with full OpenSearch semantics.
- Task, hot-threads, usage, and many admin/ops routes remain incomplete.

## Route Families

### Root

- `GET /`
- `HEAD /`

### Cluster

- `GET /_cluster/health`
- `GET /_cluster/state`
- `GET /_cluster/settings`
- `PUT /_cluster/settings`
- `GET /_cluster/pending_tasks`
- `GET /_cluster/allocation/explain`
- related reroute, search-shards, and voting-config routes from OpenSearch

### Nodes And Stats

- `GET /_nodes/stats`
- `GET /_cluster/stats`
- `GET /_stats`
- `GET /_nodes/hot_threads`
- `GET /_nodes/usage`

### Tasks And Cat

- `GET /_tasks`
- `GET /_tasks/{task_id}`
- cancel-task routes
- `/_cat/*` families used for operator summaries

## Replacement Gap

Steelsearch currently provides enough of this family for development
replacement and local compatibility checks, but not enough for production
cluster operation parity.
