#!/usr/bin/env bash
set -euo pipefail

OPENSEARCH_ROOT="${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}"
HOST="${OPENSEARCH_HTTP_HOST:-127.0.0.1}"
find_free_port() {
  python3 - "$HOST" <<'PY'
import socket
import sys

host = sys.argv[1]
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind((host, 0))
    print(sock.getsockname()[1])
PY
}

if [[ -n "${OPENSEARCH_HTTP_PORT:-}" ]]; then
  PORT="${OPENSEARCH_HTTP_PORT}"
else
  PORT="$(find_free_port)"
fi
if [[ -n "${OPENSEARCH_TRANSPORT_PORT:-}" ]]; then
  TRANSPORT_PORT="${OPENSEARCH_TRANSPORT_PORT}"
else
  TRANSPORT_PORT="9300"
fi
WORK_DIR="${OPENSEARCH_WORK_DIR:-$(mktemp -d -t opensearch-dev.XXXXXX)}"
REPO_DIR="${OPENSEARCH_REPO_DIR:-/tmp}"
CLUSTER_NAME="${OPENSEARCH_CLUSTER_NAME:-opensearch-dev}"
NODE_NAME="${OPENSEARCH_NODE_NAME:-opensearch-dev-node}"

if [[ -n "${OPENSEARCH_URL:-}" ]]; then
  echo "Using existing OpenSearch endpoint: ${OPENSEARCH_URL}" >&2
  exit 0
fi

if [[ ! -x "${OPENSEARCH_ROOT}/gradlew" ]]; then
  echo "OpenSearch checkout not found at ${OPENSEARCH_ROOT}; set OPENSEARCH_URL or OPENSEARCH_ROOT" >&2
  exit 2
fi

mkdir -p "${WORK_DIR}/data" "${WORK_DIR}/logs" "${REPO_DIR}"

echo "OpenSearch work dir: ${WORK_DIR}" >&2
echo "OpenSearch cluster: ${CLUSTER_NAME}" >&2
echo "OpenSearch node: ${NODE_NAME}" >&2
echo "OpenSearch URL: http://${HOST}:${PORT}" >&2
echo "OpenSearch transport: ${HOST}:${TRANSPORT_PORT}" >&2

cd "${OPENSEARCH_ROOT}"
exec ./gradlew run \
  -Dtests.security.manager=false \
  -Dpath.data="${WORK_DIR}/data" \
  -Dpath.logs="${WORK_DIR}/logs" \
  -Dpath.repo="${REPO_DIR}" \
  -Dhttp.host="${HOST}" \
  -Dhttp.port="${PORT}" \
  -Dtransport.port="${TRANSPORT_PORT}" \
  -Dcluster.name="${CLUSTER_NAME}" \
  -Dnode.name="${NODE_NAME}" \
  -Dopensearch.plugins.security.disabled=true
