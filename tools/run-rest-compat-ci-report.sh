#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${REST_COMPAT_WORK_DIR:-${ROOT}/target/rest-compat}"
case "${WORK_DIR}" in
  /*) ;;
  *) WORK_DIR="${ROOT}/${WORK_DIR}" ;;
esac
REPORT_PATH="${SEARCH_COMPAT_REPORT:-${WORK_DIR}/search-compat-report.json}"
case "${REPORT_PATH}" in
  /*) ;;
  *) REPORT_PATH="${ROOT}/${REPORT_PATH}" ;;
esac
WAIT_TIMEOUT="${REST_COMPAT_WAIT_TIMEOUT:-300}"
RUN_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

STEELSEARCH_PID=""
OPENSEARCH_PID=""
STEELSEARCH_START_EPOCH=""
STEELSEARCH_READY_EPOCH=""
OPENSEARCH_START_EPOCH=""
OPENSEARCH_READY_EPOCH=""

find_free_port() {
  local host="$1"
  python3 - "$host" <<'PY'
import socket
import sys

host = sys.argv[1]
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind((host, 0))
    print(sock.getsockname()[1])
PY
}

wait_for_endpoint() {
  local name="$1"
  local url="$2"
  python3 - "$name" "$url" "$WAIT_TIMEOUT" <<'PY'
import sys
import time
import urllib.request

name, url, timeout = sys.argv[1], sys.argv[2].rstrip("/"), float(sys.argv[3])
deadline = time.monotonic() + timeout
last_error = None
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(url + "/", timeout=2.0) as response:
            if response.status < 500:
                print(f"{name} ready at {url}")
                raise SystemExit(0)
    except Exception as error:  # noqa: BLE001
        last_error = error
    time.sleep(0.5)
raise SystemExit(f"{name} did not become ready at {url}: {last_error}")
PY
}

stop_process() {
  local name="$1"
  local pid="$2"
  if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
    echo "Stopping ${name} pid ${pid}" >&2
    kill "${pid}" 2>/dev/null || true
    wait "${pid}" 2>/dev/null || true
  fi
}

cleanup() {
  local status=$?
  stop_process "Steelsearch" "${STEELSEARCH_PID}"
  stop_process "OpenSearch" "${OPENSEARCH_PID}"
  exit "${status}"
}

trap cleanup EXIT INT TERM

mkdir -p "${WORK_DIR}"

if [[ -n "${STEELSEARCH_URL:-}" ]]; then
  STEELSEARCH_URL="${STEELSEARCH_URL%/}"
  STEELSEARCH_START_EPOCH="$(date +%s)"
  echo "Using existing Steelsearch endpoint: ${STEELSEARCH_URL}" >&2
else
  STEELSEARCH_START_EPOCH="$(date +%s)"
  STEELSEARCH_HTTP_HOST="${STEELSEARCH_HTTP_HOST:-127.0.0.1}"
  STEELSEARCH_HTTP_PORT="${STEELSEARCH_HTTP_PORT:-$(find_free_port "${STEELSEARCH_HTTP_HOST}")}"
  STEELSEARCH_TRANSPORT_HOST="${STEELSEARCH_TRANSPORT_HOST:-127.0.0.1}"
  STEELSEARCH_TRANSPORT_PORT="${STEELSEARCH_TRANSPORT_PORT:-$(find_free_port "${STEELSEARCH_TRANSPORT_HOST}")}"
  STEELSEARCH_WORK_DIR="${STEELSEARCH_WORK_DIR:-${WORK_DIR}/steelsearch}"
  STEELSEARCH_URL="http://${STEELSEARCH_HTTP_HOST}:${STEELSEARCH_HTTP_PORT}"
  export STEELSEARCH_HTTP_HOST STEELSEARCH_HTTP_PORT
  export STEELSEARCH_TRANSPORT_HOST STEELSEARCH_TRANSPORT_PORT STEELSEARCH_WORK_DIR
  echo "Starting Steelsearch at ${STEELSEARCH_URL}" >&2
  "${ROOT}/tools/run-steelsearch-dev.sh" >"${WORK_DIR}/steelsearch.log" 2>&1 &
  STEELSEARCH_PID=$!
fi
export STEELSEARCH_URL
wait_for_endpoint "Steelsearch" "${STEELSEARCH_URL}"
STEELSEARCH_READY_EPOCH="$(date +%s)"

if [[ -n "${OPENSEARCH_URL:-}" ]]; then
  OPENSEARCH_URL="${OPENSEARCH_URL%/}"
  OPENSEARCH_START_EPOCH="$(date +%s)"
  echo "Using existing OpenSearch endpoint: ${OPENSEARCH_URL}" >&2
else
  OPENSEARCH_START_EPOCH="$(date +%s)"
  OPENSEARCH_HTTP_HOST="${OPENSEARCH_HTTP_HOST:-127.0.0.1}"
  OPENSEARCH_HTTP_PORT="${OPENSEARCH_HTTP_PORT:-$(find_free_port "${OPENSEARCH_HTTP_HOST}")}"
  OPENSEARCH_WORK_DIR="${OPENSEARCH_WORK_DIR:-${WORK_DIR}/opensearch}"
  OPENSEARCH_URL="http://${OPENSEARCH_HTTP_HOST}:${OPENSEARCH_HTTP_PORT}"
  export OPENSEARCH_HTTP_HOST OPENSEARCH_HTTP_PORT OPENSEARCH_WORK_DIR
  echo "Starting OpenSearch at ${OPENSEARCH_URL}" >&2
  "${ROOT}/tools/run-opensearch-dev.sh" >"${WORK_DIR}/opensearch.log" 2>&1 &
  OPENSEARCH_PID=$!
fi
export OPENSEARCH_URL
wait_for_endpoint "OpenSearch" "${OPENSEARCH_URL}"
OPENSEARCH_READY_EPOCH="$(date +%s)"

cat >"${WORK_DIR}/targets.env" <<EOF
RUN_STARTED_AT=${RUN_STARTED_AT}
STEELSEARCH_URL=${STEELSEARCH_URL}
STEELSEARCH_STARTUP_SECONDS=$((STEELSEARCH_READY_EPOCH - STEELSEARCH_START_EPOCH))
OPENSEARCH_URL=${OPENSEARCH_URL}
OPENSEARCH_STARTUP_SECONDS=$((OPENSEARCH_READY_EPOCH - OPENSEARCH_START_EPOCH))
REST_COMPAT_WAIT_TIMEOUT=${WAIT_TIMEOUT}
EOF

export REQUIRE_OPENSEARCH_COMPARISON=1
export RUN_OPENSEARCH_COMPARISON=1
"${ROOT}/tools/run-search-compat.sh" \
  --wait \
  --report "${REPORT_PATH}"

echo "REST compatibility report: ${REPORT_PATH}"
