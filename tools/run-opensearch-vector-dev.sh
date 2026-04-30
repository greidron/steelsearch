#!/usr/bin/env bash
set -euo pipefail

HOST="${OPENSEARCH_HTTP_HOST:-127.0.0.1}"
PORT="${OPENSEARCH_HTTP_PORT:-9200}"
IMAGE="${OPENSEARCH_VECTOR_DOCKER_IMAGE:-opensearchproject/opensearch:2.19.0}"
CONTAINER_NAME="${OPENSEARCH_VECTOR_CONTAINER_NAME:-steelsearch-vector-opensearch}"

if [[ -n "${OPENSEARCH_URL:-}" ]]; then
  echo "Using existing OpenSearch endpoint: ${OPENSEARCH_URL}" >&2
  exit 0
fi

docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
exec docker run --rm \
  --name "${CONTAINER_NAME}" \
  -p "${HOST}:${PORT}:9200" \
  -e discovery.type=single-node \
  -e DISABLE_SECURITY_PLUGIN=true \
  -e DISABLE_INSTALL_DEMO_CONFIG=true \
  -e OPENSEARCH_JAVA_OPTS="${OPENSEARCH_JAVA_OPTS:--Xms512m -Xmx512m}" \
  "${IMAGE}"
