# Docker Replacement Scenarios

This workflow runs Steelsearch and OpenSearch side by side with Docker Compose and executes replacement-oriented checks against both services.

## Topology

- OpenSearch runs from `OPENSEARCH_IMAGE`, defaulting to `opensearchproject/opensearch:latest`, with security disabled for local compatibility testing.
- Steelsearch builds from the repository `Dockerfile` and starts three development nodes on one Compose network.
- Host ports default to:
  - OpenSearch: `http://127.0.0.1:9200`
  - Steelsearch node 1: `http://127.0.0.1:19200`
  - Steelsearch node 2: `http://127.0.0.1:19201`
  - Steelsearch node 3: `http://127.0.0.1:19202`

## Run

```bash
tools/run-docker-replacement-scenarios.sh
```

Use `KEEP_DOCKER_SCENARIO=1` to leave containers running after the test:

```bash
KEEP_DOCKER_SCENARIO=1 tools/run-docker-replacement-scenarios.sh
```

The JSON report is written to `target/docker-replacement-scenarios/report.json`.

## Covered Scenarios

1. Root and cluster health checks for both services.
2. Basic index, document, refresh, and search comparison across `match_all`, `match`, `term`, and `range` queries.
3. OpenSearch-to-Steelsearch migration rehearsal:
   - create and load a source index in OpenSearch
   - export source documents through `_search`
   - create and load a target index in Steelsearch
   - validate document count and source checksum parity
4. Steelsearch MiniLM-compatible ML Commons lifecycle and k-NN search:
   - register and deploy an `all-MiniLM-L6-v2` style embedding model
   - predict vectors through `_plugins/_ml/models/{model_id}/_predict`
   - create a `knn_vector` index
   - index predicted vectors and execute a k-NN query

## Scope Notes

The default OpenSearch Docker image is not treated as a k-NN or ML plugin image. The Docker replacement run therefore validates k-NN and MiniLM-compatible embedding behavior on Steelsearch, while generic OpenSearch parity checks cover REST indexing, search, and migration. To run OpenSearch k-NN parity, set `OPENSEARCH_IMAGE` to an image that includes the OpenSearch k-NN plugin and add a plugin-specific parity case to `tools/docker_replacement_scenarios.py`.
