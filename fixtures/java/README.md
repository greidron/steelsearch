# Java Fixture Workflow

This directory contains a small Java program that emits OpenSearch transport
bytes using the real Java implementation from a local OpenSearch checkout. The
generated fixture file is the Rust test source of truth for wire and
cluster-state compatibility.

## Files

- `src/org/opensearch/transport/OpenSearchWireFixture.java`: Java fixture
  generator compiled against OpenSearch classes.
- `opensearch-wire-fixtures.txt`: checked-in generated fixture output consumed
  by Rust tests.
- `../../tools/run-java-fixture.sh`: reproducible wrapper that resolves the
  OpenSearch classpath, compiles the generator into a temporary output
  directory, and prints fixture lines to stdout.
- `../../tools/print-opensearch-classpath.init.gradle`: Gradle init script used
  by the wrapper to ask the OpenSearch build for the server runtime classpath.

## Requirements

- A local OpenSearch checkout. By default the wrapper uses
  `/home/ubuntu/OpenSearch`; override with `OPENSEARCH_ROOT=/path/to/OpenSearch`.
- The OpenSearch checkout must be at the compatibility target revision for the
  fixtures being updated. Record any intentional target change in
  `docs/rust-port/compatibility-targets.md`.
- JDK and Gradle requirements are inherited from the OpenSearch checkout.

## Reproduce Existing Output

From the SteelSearch repository root:

```bash
OPENSEARCH_ROOT=/home/ubuntu/OpenSearch \
  tools/run-java-fixture.sh > /tmp/opensearch-wire-fixtures.txt

diff -u fixtures/java/opensearch-wire-fixtures.txt /tmp/opensearch-wire-fixtures.txt
```

An empty diff means the checked-in fixtures are reproducible from the local
OpenSearch checkout.

## Update Fixtures

When fixture behavior intentionally changes, regenerate and then run the Rust
fixture tests:

```bash
OPENSEARCH_ROOT=/home/ubuntu/OpenSearch \
  tools/run-java-fixture.sh > fixtures/java/opensearch-wire-fixtures.txt

cargo test -p os-cluster-state --test java_fixtures
```

If transport framing or handshake bytes changed, also run the affected
transport and wire tests before committing:

```bash
cargo test -p os-transport -p os-wire
```

## Reproducibility Notes

- The wrapper writes compiled fixture classes under
  `OUT_DIR=/tmp/opensearch-fixture-classes` by default. Override `OUT_DIR` only
  when isolating concurrent fixture runs.
- The Java generator should avoid wall-clock timestamps, random UUIDs, temporary
  paths that vary per machine, and map/set iteration orders that are not stable.
- New fixture lines should use deterministic names and values so changes in
  `opensearch-wire-fixtures.txt` are meaningful in review.
- Keep this README updated when adding a new fixture command, environment
  variable, or OpenSearch checkout requirement.

## Fixture Coverage

The fixture set covers:

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
