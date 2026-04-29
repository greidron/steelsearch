# Docker Replacement Rehearsal

This scenario starts OpenSearch and a three-node Steelsearch cluster with
Docker Compose, runs supported compatibility checks, performs an
OpenSearch-to-Steelsearch bulk migration rehearsal, and verifies the
Steelsearch MiniLM-compatible embedding to k-NN search flow.

## Run

```bash
tools/run-docker-replacement-rehearsal.sh
```

Useful environment overrides:

```bash
OPENSEARCH_IMAGE=opensearchproject/opensearch:latest
STEELSEARCH_HTTP_PORT=29201
OPENSEARCH_HTTP_PORT=29200
KEEP_DOCKER_REHEARSAL=1
REPORT_DIR=target/docker-replacement-rehearsal
```

## Reports

The script writes:

- `search-compat-report.json`: supported REST/search fixture comparison between
  Steelsearch and OpenSearch.
- `docker-replacement-scenarios.json`: Docker-level smoke, text search
  comparison, OpenSearch export/import migration validation, and Steelsearch
  `all-MiniLM-L6-v2`-compatible k-NN validation.

The scenario script lives at
`supports/integration_test/docker_replacement_scenarios.py`; `tools/` contains
the runnable rehearsal wrapper.

OpenSearch k-NN comparison depends on the Docker image including the OpenSearch
k-NN plugin. If the image rejects `knn_vector` mappings or `knn` queries, the
migration report records that as an explicit unsupported OpenSearch-side vector
comparison gap while still validating lexical document migration.
