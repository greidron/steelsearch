#!/usr/bin/env bash
set -euo pipefail

find_free_port() {
  python3 - <<'PY'
import socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

WORK_DIR="${1:-$(mktemp -d -t java-java-direct.XXXXXX)}"
mkdir -p "${WORK_DIR}/primary" "${WORK_DIR}/follower"

PRIMARY_HTTP_PORT="$(find_free_port)"
PRIMARY_TRANSPORT_PORT="$(find_free_port)"
FOLLOWER_HTTP_PORT="$(find_free_port)"
FOLLOWER_TRANSPORT_PORT="$(find_free_port)"
CLUSTER_NAME="java-java-direct-ref"
PRIMARY_NAME="java-primary-1"
FOLLOWER_NAME="java-follower-1"
INITIAL_MANAGERS="${PRIMARY_NAME},${FOLLOWER_NAME}"

cleanup() {
  set +e
  [[ -n "${PRIMARY_PID:-}" ]] && kill "${PRIMARY_PID}" 2>/dev/null
  [[ -n "${FOLLOWER_PID:-}" ]] && kill "${FOLLOWER_PID}" 2>/dev/null
  wait "${PRIMARY_PID:-}" 2>/dev/null
  wait "${FOLLOWER_PID:-}" 2>/dev/null
}
trap cleanup EXIT

OPENSEARCH_WORK_DIR="${WORK_DIR}/follower" \
OPENSEARCH_HTTP_PORT="${FOLLOWER_HTTP_PORT}" \
OPENSEARCH_TRANSPORT_PORT="${FOLLOWER_TRANSPORT_PORT}" \
OPENSEARCH_CLUSTER_NAME="${CLUSTER_NAME}" \
OPENSEARCH_NODE_NAME="${FOLLOWER_NAME}" \
OPENSEARCH_INITIAL_CLUSTER_MANAGER_NODES="${INITIAL_MANAGERS}" \
OPENSEARCH_DISCOVERY_SEED_HOSTS="127.0.0.1:${PRIMARY_TRANSPORT_PORT}" \
bash tools/run-opensearch-dev.sh \
  >"${WORK_DIR}/follower/stdout.log" 2>"${WORK_DIR}/follower/stderr.log" &
FOLLOWER_PID=$!

sleep 8

OPENSEARCH_WORK_DIR="${WORK_DIR}/primary" \
OPENSEARCH_HTTP_PORT="${PRIMARY_HTTP_PORT}" \
OPENSEARCH_TRANSPORT_PORT="${PRIMARY_TRANSPORT_PORT}" \
OPENSEARCH_CLUSTER_NAME="${CLUSTER_NAME}" \
OPENSEARCH_NODE_NAME="${PRIMARY_NAME}" \
OPENSEARCH_INITIAL_CLUSTER_MANAGER_NODES="${INITIAL_MANAGERS}" \
OPENSEARCH_DISCOVERY_SEED_HOSTS="127.0.0.1:${FOLLOWER_TRANSPORT_PORT}" \
bash tools/run-opensearch-dev.sh \
  >"${WORK_DIR}/primary/stdout.log" 2>"${WORK_DIR}/primary/stderr.log" &
PRIMARY_PID=$!

sleep 20

OBSERVED_NODE_COUNT="$(curl -fsS "http://127.0.0.1:${PRIMARY_HTTP_PORT}/_cat/nodes?h=name" | sed '/^$/d' | wc -l | tr -d ' ')"

cleanup
trap - EXIT

cat <<EOF
{
  "work_dir": "${WORK_DIR}",
  "primary_stdout": "${WORK_DIR}/primary/stdout.log",
  "primary_stderr": "${WORK_DIR}/primary/stderr.log",
  "follower_stdout": "${WORK_DIR}/follower/stdout.log",
  "follower_stderr": "${WORK_DIR}/follower/stderr.log",
  "observed_node_count": ${OBSERVED_NODE_COUNT}
}
EOF
