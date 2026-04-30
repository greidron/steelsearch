#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${STEELSEARCH_HTTP_HOST:-0.0.0.0}"
TRANSPORT_HOST="${STEELSEARCH_TRANSPORT_HOST:-0.0.0.0}"
HTTP_ACCESS_HOST="${STEELSEARCH_HTTP_ACCESS_HOST:-127.0.0.1}"
TRANSPORT_ACCESS_HOST="${STEELSEARCH_TRANSPORT_ACCESS_HOST:-127.0.0.1}"
WORK_DIR="${STEELSEARCH_WORK_DIR:-$(mktemp -d -t steelsearch-dev.XXXXXX)}"

find_free_port() {
  python3 - "$1" <<'PY'
import socket
import sys

host = sys.argv[1]
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind((host, 0))
    print(sock.getsockname()[1])
PY
}

if [[ -n "${STEELSEARCH_HTTP_PORT:-}" ]]; then
  PORT="${STEELSEARCH_HTTP_PORT}"
else
  PORT="$(find_free_port "${HOST}")"
fi

if [[ -n "${STEELSEARCH_TRANSPORT_PORT:-}" ]]; then
  TRANSPORT_PORT="${STEELSEARCH_TRANSPORT_PORT}"
else
  TRANSPORT_PORT="$(find_free_port "${TRANSPORT_HOST}")"
fi

mkdir -p "${WORK_DIR}/data" "${WORK_DIR}/logs"
export STEELSEARCH_DATA_PATH="${STEELSEARCH_DATA_PATH:-${WORK_DIR}/data}"
export STEELSEARCH_LOG_PATH="${STEELSEARCH_LOG_PATH:-${WORK_DIR}/logs}"

echo "Steelsearch work dir: ${WORK_DIR}" >&2
echo "Steelsearch bind URL: http://${HOST}:${PORT}" >&2
echo "Steelsearch access URL: http://${HTTP_ACCESS_HOST}:${PORT}" >&2
echo "Steelsearch transport bind: ${TRANSPORT_HOST}:${TRANSPORT_PORT}" >&2
echo "Steelsearch transport access: ${TRANSPORT_ACCESS_HOST}:${TRANSPORT_PORT}" >&2

exec cargo run -p os-node --features standalone-runtime --bin steelsearch --manifest-path "${ROOT}/Cargo.toml" -- \
  --http.host "${HOST}" \
  --http.port "${PORT}" \
  --transport.host "${TRANSPORT_HOST}" \
  --transport.port "${TRANSPORT_PORT}" \
  --node.id "${STEELSEARCH_NODE_ID:-${STEELSEARCH_NODE_NAME:-steelsearch-dev-node}}" \
  --node.name "${STEELSEARCH_NODE_NAME:-steelsearch-dev-node}" \
  --node.roles "${STEELSEARCH_NODE_ROLES:-cluster_manager,data,ingest}" \
  --cluster.name "${STEELSEARCH_CLUSTER_NAME:-steelsearch-dev}" \
  --discovery.seed_hosts "${STEELSEARCH_DISCOVERY_SEED_HOSTS:-}" \
  --path.data "${STEELSEARCH_DATA_PATH}"
