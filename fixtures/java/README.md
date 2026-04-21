# Java Fixture Plan

This directory will hold a small Java program that emits OpenSearch transport
bytes using the real Java implementation from `/home/ubuntu/OpenSearch`.

The first fixture set should cover:

- `TcpHeader`
- Java `StreamOutput.writeString`
- string arrays
- thread-context request/response headers
- `internal:tcp/handshake` request
- `internal:transport/handshake` request
- cluster-state response bodies
- publication cluster-state diff bodies, including an empty diff,
  delete-only top-level custom/routing index/metadata index/metadata template
  and metadata custom map diffs, a delete-only consistent-setting hash diff,
  routing/metadata index upsert diffs, routing and metadata index named diffs,
  nested metadata index mapping, alias, custom-data, rollover-info, in-sync
  allocation ids, and split-shards diffs, metadata template upsert and named
  diffs including a mapping/alias replacement, and metadata custom upsert
  diffs including repositories,
  component-template, composable
  index-template, data-stream, ingest, search-pipeline, stored-scripts,
  index-graveyard, persistent-tasks, decommission, weighted-routing, view, and
  workload-group variants, `repositories`, `view`, `queryGroups`,
  `data_stream`, `component_template`, `index_template`,
  `weighted_shard_routing`, and `decommissionedAttribute` metadata custom named
  diffs, plus
  a top-level
  `snapshots` custom upsert diff with empty and non-empty payload variants and
  a top-level `snapshots` custom named diff with a shard-status replacement,
  plus top-level `restore` custom upsert diffs with empty and shard-status
  payload variants, a top-level `restore` custom named diff with a shard-status
  replacement, top-level `snapshot_deletions` custom upsert and named diffs,
  and a top-level `repository_cleanup` custom upsert diff and named diff

The Rust side should treat these fixture bytes as the compatibility source of
truth for the wire and cluster-state milestones.

## Current Workflow

1. Build the required OpenSearch classes:

```bash
cd /home/ubuntu/OpenSearch
./gradlew :libs:opensearch-core:classes :server:classes
```

2. Emit the fixtures:

```bash
/home/ubuntu/steelsearch/tools/run-java-fixture.sh
```

3. Compare the output with `opensearch-wire-fixtures.txt`.
