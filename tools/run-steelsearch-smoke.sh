#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SMOKE_DIR="${STEELSEARCH_SMOKE_DIR:-$(mktemp -d -t steelsearch-smoke.XXXXXX)}"
HOST="${STEELSEARCH_HTTP_HOST:-127.0.0.1}"
WAIT_TIMEOUT="${STEELSEARCH_SMOKE_WAIT_TIMEOUT:-120}"
PID=""

usage() {
  cat <<'USAGE'
Run a local Steelsearch daemon smoke test.

Environment:
  STEELSEARCH_URL                 Reuse an existing Steelsearch endpoint.
  STEELSEARCH_HTTP_HOST           Host for a daemon started here. Default: 127.0.0.1.
  STEELSEARCH_HTTP_PORT           Port for a daemon started here. Default: random free port.
  STEELSEARCH_TRANSPORT_PORT      Transport port for a daemon started here. Default: random free port.
  STEELSEARCH_SMOKE_DIR           Work/log directory. Default: mktemp.
  STEELSEARCH_SMOKE_WAIT_TIMEOUT  Startup wait timeout in seconds. Default: 120.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

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

cleanup() {
  local status=$?
  if [[ -n "${PID}" ]] && kill -0 "${PID}" 2>/dev/null; then
    kill "${PID}" 2>/dev/null || true
    wait "${PID}" 2>/dev/null || true
  fi
  if [[ "${status}" != "0" && -n "${SMOKE_DIR}" ]]; then
    echo "Steelsearch smoke logs: ${SMOKE_DIR}/logs" >&2
    tail -120 "${SMOKE_DIR}/logs/stderr.log" >&2 2>/dev/null || true
  fi
  exit "${status}"
}
trap cleanup EXIT INT TERM

wait_for_endpoint() {
  local url="$1"
  python3 - "$url" "$WAIT_TIMEOUT" <<'PY'
import sys
import time
import urllib.request

url, timeout = sys.argv[1].rstrip("/"), float(sys.argv[2])
deadline = time.monotonic() + timeout
last_error = None
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(url + "/", timeout=2.0) as response:
            if response.status < 500:
                raise SystemExit(0)
    except Exception as error:  # noqa: BLE001
        last_error = error
    time.sleep(0.25)
raise SystemExit(f"Steelsearch did not become ready at {url}: {last_error}")
PY
}

if [[ -n "${STEELSEARCH_URL:-}" ]]; then
  URL="${STEELSEARCH_URL%/}"
  echo "Using existing Steelsearch endpoint: ${URL}" >&2
else
  PORT="${STEELSEARCH_HTTP_PORT:-$(find_free_port "${HOST}")}"
  TRANSPORT_PORT="${STEELSEARCH_TRANSPORT_PORT:-$(find_free_port "${HOST}")}"
  URL="http://${HOST}:${PORT}"
  mkdir -p "${SMOKE_DIR}/logs"
  export STEELSEARCH_HTTP_HOST="${HOST}"
  export STEELSEARCH_HTTP_PORT="${PORT}"
  export STEELSEARCH_TRANSPORT_PORT="${TRANSPORT_PORT}"
  export STEELSEARCH_WORK_DIR="${SMOKE_DIR}/node"
  echo "Starting Steelsearch smoke daemon at ${URL}" >&2
  "${ROOT}/tools/run-steelsearch-dev.sh" >"${SMOKE_DIR}/logs/stdout.log" 2>"${SMOKE_DIR}/logs/stderr.log" &
  PID=$!
fi

wait_for_endpoint "${URL}"

curl -fsS "${URL}/" >/dev/null
curl -fsS "${URL}/_cluster/health" >/dev/null
curl -fsS "${URL}/_nodes/stats" >/dev/null
curl -fsS "${URL}/_steelsearch/readiness" >/dev/null

echo "Steelsearch daemon smoke passed: ${URL}"
