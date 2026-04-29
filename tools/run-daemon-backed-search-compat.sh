#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${DAEMON_SEARCH_COMPAT_WORK_DIR:-$(mktemp -d -p "${ROOT}/target" daemon-search-compat.XXXXXX)}"
case "${WORK_DIR}" in
  /*) ;;
  *) WORK_DIR="${ROOT}/${WORK_DIR}" ;;
esac
WAIT_TIMEOUT="${DAEMON_SEARCH_COMPAT_WAIT_TIMEOUT:-300}"
HOST="${STEELSEARCH_HTTP_HOST:-127.0.0.1}"
TRANSPORT_HOST="${STEELSEARCH_TRANSPORT_HOST:-127.0.0.1}"
DRY_RUN=0

STEELSEARCH_PID=""
STARTED_DAEMON=0

usage() {
  cat <<'USAGE'
Run search compatibility fixtures against a live Steelsearch daemon lifecycle.

Usage:
  tools/run-daemon-backed-search-compat.sh [--dry-run] [args passed to run-search-compat.sh]

Environment:
  STEELSEARCH_URL                    Reuse an existing Steelsearch endpoint.
  STEELSEARCH_HTTP_HOST              Host for a daemon started here. Default: 127.0.0.1.
  STEELSEARCH_HTTP_PORT              Port for a daemon started here. Default: random free port.
  STEELSEARCH_TRANSPORT_HOST         Transport host for a daemon started here. Default: 127.0.0.1.
  STEELSEARCH_TRANSPORT_PORT         Transport port for a daemon started here. Default: random free port.
  DAEMON_SEARCH_COMPAT_WORK_DIR      Output/log directory. Default: mktemp under target/.
  DAEMON_SEARCH_COMPAT_WAIT_TIMEOUT  Startup wait timeout in seconds. Default: 300.

All arguments are passed through to tools/run-search-compat.sh.
USAGE
}

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

run() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '+'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

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
    time.sleep(0.5)
raise SystemExit(f"Steelsearch did not become ready at {url}: {last_error}")
PY
}

cleanup() {
  local status=$?
  if [[ "${STARTED_DAEMON}" == "1" && -n "${STEELSEARCH_PID}" ]] && kill -0 "${STEELSEARCH_PID}" 2>/dev/null; then
    kill "${STEELSEARCH_PID}" 2>/dev/null || true
    wait "${STEELSEARCH_PID}" 2>/dev/null || true
  fi
  if [[ "${status}" != "0" && -f "${WORK_DIR}/steelsearch.log" ]]; then
    echo "Daemon-backed search compat log: ${WORK_DIR}/steelsearch.log" >&2
    tail -120 "${WORK_DIR}/steelsearch.log" >&2 2>/dev/null || true
  fi
  exit "${status}"
}
trap cleanup EXIT INT TERM

mkdir -p "${WORK_DIR}"
cd "${ROOT}"

if [[ -n "${STEELSEARCH_URL:-}" ]]; then
  STEELSEARCH_URL="${STEELSEARCH_URL%/}"
  echo "Using existing Steelsearch endpoint: ${STEELSEARCH_URL}" >&2
else
  STEELSEARCH_HTTP_PORT="${STEELSEARCH_HTTP_PORT:-$(find_free_port "${HOST}")}"
  STEELSEARCH_TRANSPORT_PORT="${STEELSEARCH_TRANSPORT_PORT:-$(find_free_port "${TRANSPORT_HOST}")}"
  STEELSEARCH_URL="http://${HOST}:${STEELSEARCH_HTTP_PORT}"
  export STEELSEARCH_HTTP_HOST="${HOST}"
  export STEELSEARCH_HTTP_PORT
  export STEELSEARCH_TRANSPORT_HOST="${TRANSPORT_HOST}"
  export STEELSEARCH_TRANSPORT_PORT
  export STEELSEARCH_WORK_DIR="${STEELSEARCH_WORK_DIR:-${WORK_DIR}/steelsearch}"
  echo "Starting Steelsearch at ${STEELSEARCH_URL}" >&2
  if [[ "${DRY_RUN}" == "1" ]]; then
    run tools/run-steelsearch-dev.sh
  else
    tools/run-steelsearch-dev.sh >"${WORK_DIR}/steelsearch.log" 2>&1 &
    STEELSEARCH_PID=$!
    STARTED_DAEMON=1
  fi
fi

export STEELSEARCH_URL
if [[ "${DRY_RUN}" == "1" ]]; then
  printf '+ export STEELSEARCH_URL=%q\n' "${STEELSEARCH_URL}"
else
  wait_for_endpoint "${STEELSEARCH_URL}"
fi
run tools/run-search-compat.sh "$@"
