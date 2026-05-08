#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${STEELSEARCH_HTTP_HOST:-0.0.0.0}"
TRANSPORT_HOST="${STEELSEARCH_TRANSPORT_HOST:-0.0.0.0}"
HTTP_ACCESS_HOST="${STEELSEARCH_HTTP_ACCESS_HOST:-127.0.0.1}"
TRANSPORT_ACCESS_HOST="${STEELSEARCH_TRANSPORT_ACCESS_HOST:-127.0.0.1}"
WORK_DIR="${STEELSEARCH_WORK_DIR:-$(mktemp -d -t steelsearch-dev.XXXXXX)}"
SPLIT_BUILD_RUN="${STEELSEARCH_SPLIT_BUILD_RUN:-0}"

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
echo "Steelsearch cargo run launch epoch ms: $(python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
)" >&2

args=(
  cargo run -p os-node --features standalone-runtime --bin steelsearch --manifest-path "${ROOT}/Cargo.toml" --
  --http.host "${HOST}"
  --http.port "${PORT}"
  --transport.host "${TRANSPORT_HOST}"
  --transport.port "${TRANSPORT_PORT}"
  --node.id "${STEELSEARCH_NODE_ID:-${STEELSEARCH_NODE_NAME:-steelsearch-dev-node}}"
  --node.name "${STEELSEARCH_NODE_NAME:-steelsearch-dev-node}"
  --node.roles "${STEELSEARCH_NODE_ROLES:-cluster_manager,data,ingest,remote_cluster_client}"
  --cluster.name "${STEELSEARCH_CLUSTER_NAME:-steelsearch-dev}"
  --path.data "${STEELSEARCH_DATA_PATH}"
)

if [[ -n "${STEELSEARCH_DISCOVERY_SEED_HOSTS:-}" ]]; then
  args+=(--discovery.seed_hosts "${STEELSEARCH_DISCOVERY_SEED_HOSTS}")
fi

if [[ -n "${STEELSEARCH_MODE:-}" ]]; then
  args+=(--mode "${STEELSEARCH_MODE}")
fi

if [[ -n "${STEELSEARCH_JAVA_WRITE_FORWARDING_VALIDATED:-}" ]]; then
  args+=(--interop.java_write_forwarding_validated "${STEELSEARCH_JAVA_WRITE_FORWARDING_VALIDATED}")
fi

if [[ -n "${STEELSEARCH_INTEROP_SEED_PEER_IDENTITY_MANIFEST:-}" ]]; then
  args+=(--interop.seed_peer_identity_manifest "${STEELSEARCH_INTEROP_SEED_PEER_IDENTITY_MANIFEST}")
fi

if [[ "${STEELSEARCH_DEV_DRY_RUN:-0}" == "1" ]]; then
  printf '%q ' "${args[@]}"
  printf '\n'
  exit 0
fi

if [[ "${SPLIT_BUILD_RUN}" == "1" ]]; then
  echo "Steelsearch cargo build start epoch ms: $(python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
)" >&2
  cargo build -p os-node --features standalone-runtime --bin steelsearch --manifest-path "${ROOT}/Cargo.toml"
  echo "Steelsearch cargo build done epoch ms: $(python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
)" >&2
  echo "Steelsearch binary exec launch epoch ms: $(python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
)" >&2
  exec "${ROOT}/target/debug/steelsearch" "${args[@]:11}"
fi

exec "${args[@]}"
