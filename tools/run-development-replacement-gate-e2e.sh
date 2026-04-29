#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${DEVELOPMENT_REPLACEMENT_GATE_E2E_WORK_DIR:-$(mktemp -d -p "${ROOT}/target" development-replacement-gate-e2e.XXXXXX)}"
case "${WORK_DIR}" in
  /*) ;;
  *) WORK_DIR="${ROOT}/${WORK_DIR}" ;;
esac
WAIT_TIMEOUT="${DEVELOPMENT_REPLACEMENT_GATE_E2E_WAIT_TIMEOUT:-300}"
HOST="${STEELSEARCH_HTTP_HOST:-127.0.0.1}"
TRANSPORT_HOST="${STEELSEARCH_TRANSPORT_HOST:-127.0.0.1}"
DRY_RUN=0
STEELSEARCH_PID=""

usage() {
  cat <<'USAGE'
Boot a live Steelsearch daemon and execute the full development replacement gate.

Usage:
  tools/run-development-replacement-gate-e2e.sh [--dry-run]

Environment:
  DEVELOPMENT_REPLACEMENT_GATE_E2E_WORK_DIR      Output/log directory.
                                                 Default: mktemp under target/
  DEVELOPMENT_REPLACEMENT_GATE_E2E_WAIT_TIMEOUT  Startup wait timeout in seconds.
                                                 Default: 300
  STEELSEARCH_HTTP_HOST                          Host for the daemon started here.
                                                 Default: 127.0.0.1
  STEELSEARCH_HTTP_PORT                          HTTP port for the daemon started here.
                                                 Default: random free port
  STEELSEARCH_TRANSPORT_HOST                     Transport host for the daemon started here.
                                                 Default: 127.0.0.1
  STEELSEARCH_TRANSPORT_PORT                     Transport port for the daemon started here.
                                                 Default: random free port
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

if [[ "$#" -ne 0 ]]; then
  usage >&2
  exit 2
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
  if [[ -n "${STEELSEARCH_PID}" ]] && kill -0 "${STEELSEARCH_PID}" 2>/dev/null; then
    kill "${STEELSEARCH_PID}" 2>/dev/null || true
    wait "${STEELSEARCH_PID}" 2>/dev/null || true
  fi
  if [[ "${status}" != "0" && -f "${WORK_DIR}/steelsearch.log" ]]; then
    echo "Development replacement gate e2e log: ${WORK_DIR}/steelsearch.log" >&2
    tail -120 "${WORK_DIR}/steelsearch.log" >&2 2>/dev/null || true
  fi
  exit "${status}"
}
trap cleanup EXIT INT TERM

mkdir -p "${WORK_DIR}"
cd "${ROOT}"

STEELSEARCH_HTTP_PORT="${STEELSEARCH_HTTP_PORT:-$(find_free_port "${HOST}")}"
STEELSEARCH_TRANSPORT_PORT="${STEELSEARCH_TRANSPORT_PORT:-$(find_free_port "${TRANSPORT_HOST}")}"
STEELSEARCH_URL="http://${HOST}:${STEELSEARCH_HTTP_PORT}"
export STEELSEARCH_HTTP_HOST="${HOST}"
export STEELSEARCH_HTTP_PORT
export STEELSEARCH_TRANSPORT_HOST="${TRANSPORT_HOST}"
export STEELSEARCH_TRANSPORT_PORT
export STEELSEARCH_WORK_DIR="${STEELSEARCH_WORK_DIR:-${WORK_DIR}/steelsearch}"
export STEELSEARCH_URL

if [[ "${DRY_RUN}" == "1" ]]; then
  printf '+ export STEELSEARCH_URL=%q\n' "${STEELSEARCH_URL}"
  printf '+ export STEELSEARCH_HTTP_HOST=%q\n' "${STEELSEARCH_HTTP_HOST}"
  printf '+ export STEELSEARCH_HTTP_PORT=%q\n' "${STEELSEARCH_HTTP_PORT}"
  printf '+ export STEELSEARCH_TRANSPORT_HOST=%q\n' "${STEELSEARCH_TRANSPORT_HOST}"
  printf '+ export STEELSEARCH_TRANSPORT_PORT=%q\n' "${STEELSEARCH_TRANSPORT_PORT}"
  printf '+ export STEELSEARCH_WORK_DIR=%q\n' "${STEELSEARCH_WORK_DIR}"
  printf '+ tools/run-steelsearch-dev.sh >%q 2>&1 &\n' "${WORK_DIR}/steelsearch.log"
  printf '+ wait_for_endpoint %q\n' "${STEELSEARCH_URL}"
  printf '+ tools/run-development-replacement-gate.sh\n'
  exit 0
fi

tools/run-steelsearch-dev.sh >"${WORK_DIR}/steelsearch.log" 2>&1 &
STEELSEARCH_PID=$!
wait_for_endpoint "${STEELSEARCH_URL}"
tools/run-development-replacement-gate.sh
