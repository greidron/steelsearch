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

wait_for_started() {
  local logfile=$1
  local timeout_seconds=${2:-60}
  local waited=0
  while (( waited < timeout_seconds )); do
    if [[ -f "$logfile" ]] && rg -q "started|publish_address" "$logfile"; then
      return 0
    fi
    sleep 1
    waited=$(( waited + 1 ))
  done
  return 1
}

WORK_DIR="${1:-$(mktemp -d -t java-java-publish-state.XXXXXX)}"
mkdir -p "${WORK_DIR}/proxy" "${WORK_DIR}/primary" "${WORK_DIR}/follower"

PRIMARY_HTTP_PORT="$(find_free_port)"
PRIMARY_TRANSPORT_PORT="$(find_free_port)"
FOLLOWER_HTTP_PORT="$(find_free_port)"
FOLLOWER_TRANSPORT_PORT="$(find_free_port)"
PROXY_PORT="$(find_free_port)"
CLUSTER_NAME="java-java-publish-ref"
PRIMARY_NAME="java-primary-1"
FOLLOWER_NAME="java-follower-1"
INITIAL_MANAGERS="${PRIMARY_NAME},${FOLLOWER_NAME}"

cleanup() {
  set +e
  [[ -n "${PRIMARY_PID:-}" ]] && kill "${PRIMARY_PID}" 2>/dev/null
  [[ -n "${FOLLOWER_PID:-}" ]] && kill "${FOLLOWER_PID}" 2>/dev/null
  [[ -n "${PROXY_PID:-}" ]] && kill "${PROXY_PID}" 2>/dev/null
  wait "${PRIMARY_PID:-}" 2>/dev/null
  wait "${FOLLOWER_PID:-}" 2>/dev/null
  wait "${PROXY_PID:-}" 2>/dev/null
}
trap cleanup EXIT

python3 tools/capture_transport_proxy.py \
  --listen-host 127.0.0.1 \
  --listen-port "${PROXY_PORT}" \
  --target-host 127.0.0.1 \
  --target-port "${FOLLOWER_TRANSPORT_PORT}" \
  --report-path "${WORK_DIR}/proxy/capture.json" \
  >"${WORK_DIR}/proxy/stdout.log" 2>"${WORK_DIR}/proxy/stderr.log" &
PROXY_PID=$!

OPENSEARCH_WORK_DIR="${WORK_DIR}/follower" \
OPENSEARCH_HTTP_PORT="${FOLLOWER_HTTP_PORT}" \
OPENSEARCH_TRANSPORT_PORT="${FOLLOWER_TRANSPORT_PORT}" \
OPENSEARCH_TRANSPORT_PUBLISH_HOST="127.0.0.1" \
OPENSEARCH_TRANSPORT_PUBLISH_PORT="${PROXY_PORT}" \
OPENSEARCH_CLUSTER_NAME="${CLUSTER_NAME}" \
OPENSEARCH_NODE_NAME="${FOLLOWER_NAME}" \
OPENSEARCH_INITIAL_CLUSTER_MANAGER_NODES="${INITIAL_MANAGERS}" \
OPENSEARCH_DISCOVERY_SEED_HOSTS="127.0.0.1:${PRIMARY_TRANSPORT_PORT}" \
bash tools/run-opensearch-dev.sh \
  >"${WORK_DIR}/follower/stdout.log" 2>"${WORK_DIR}/follower/stderr.log" &
FOLLOWER_PID=$!

wait_for_started "${WORK_DIR}/follower/stdout.log" 60

OPENSEARCH_WORK_DIR="${WORK_DIR}/primary" \
OPENSEARCH_HTTP_PORT="${PRIMARY_HTTP_PORT}" \
OPENSEARCH_TRANSPORT_PORT="${PRIMARY_TRANSPORT_PORT}" \
OPENSEARCH_CLUSTER_NAME="${CLUSTER_NAME}" \
OPENSEARCH_NODE_NAME="${PRIMARY_NAME}" \
OPENSEARCH_INITIAL_CLUSTER_MANAGER_NODES="${INITIAL_MANAGERS}" \
OPENSEARCH_DISCOVERY_SEED_HOSTS="127.0.0.1:${PROXY_PORT}" \
bash tools/run-opensearch-dev.sh \
  >"${WORK_DIR}/primary/stdout.log" 2>"${WORK_DIR}/primary/stderr.log" &
PRIMARY_PID=$!

wait_for_started "${WORK_DIR}/primary/stdout.log" 60 || true
sleep 20

cleanup
trap - EXIT

cat <<EOF
{
  "work_dir": "${WORK_DIR}",
  "proxy_capture": "${WORK_DIR}/proxy/capture.json",
  "primary_stdout": "${WORK_DIR}/primary/stdout.log",
  "primary_stderr": "${WORK_DIR}/primary/stderr.log",
  "follower_stdout": "${WORK_DIR}/follower/stdout.log",
  "follower_stderr": "${WORK_DIR}/follower/stderr.log"
}
EOF
