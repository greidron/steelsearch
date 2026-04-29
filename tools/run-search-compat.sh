#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE_PATH="${ROOT}/tools/fixtures/search-compat.json"
REPORT_PATH="${ROOT}/target/search-compat-report.json"
SEARCH_COMPAT_DIR="${SEARCH_COMPAT_DIR:-$(mktemp -d -t steelsearch-search-compat.XXXXXX)}"
SEARCH_COMPAT_WAIT_TIMEOUT="${SEARCH_COMPAT_WAIT_TIMEOUT:-120}"
STEELSEARCH_PID=""

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
  if [[ -n "${STEELSEARCH_PID}" ]] && kill -0 "${STEELSEARCH_PID}" 2>/dev/null; then
    kill "${STEELSEARCH_PID}" 2>/dev/null || true
    wait "${STEELSEARCH_PID}" 2>/dev/null || true
  fi
  if [[ "${status}" != "0" && -n "${SEARCH_COMPAT_DIR}" ]]; then
    echo "Search compat logs: ${SEARCH_COMPAT_DIR}/logs" >&2
    tail -120 "${SEARCH_COMPAT_DIR}/logs/stderr.log" >&2 2>/dev/null || true
  fi
  exit "${status}"
}
trap cleanup EXIT INT TERM

wait_for_endpoint() {
  local url="$1"
  python3 - "$url" "$SEARCH_COMPAT_WAIT_TIMEOUT" <<'PY'
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

if [[ -z "${STEELSEARCH_URL:-}" ]]; then
  HOST="${STEELSEARCH_HTTP_HOST:-127.0.0.1}"
  PORT="${STEELSEARCH_HTTP_PORT:-$(find_free_port "${HOST}")}"
  TRANSPORT_PORT="${STEELSEARCH_TRANSPORT_PORT:-$(find_free_port "${HOST}")}"
  mkdir -p "${SEARCH_COMPAT_DIR}/logs"
  export STEELSEARCH_HTTP_HOST="${HOST}"
  export STEELSEARCH_HTTP_PORT="${PORT}"
  export STEELSEARCH_TRANSPORT_PORT="${TRANSPORT_PORT}"
  export STEELSEARCH_WORK_DIR="${SEARCH_COMPAT_DIR}/node"
  STEELSEARCH_URL="http://${HOST}:${PORT}"
  export STEELSEARCH_URL
  echo "Starting Steelsearch for search compatibility at ${STEELSEARCH_URL}" >&2
  "${ROOT}/tools/run-steelsearch-dev.sh" >"${SEARCH_COMPAT_DIR}/logs/stdout.log" 2>"${SEARCH_COMPAT_DIR}/logs/stderr.log" &
  STEELSEARCH_PID=$!
  wait_for_endpoint "${STEELSEARCH_URL}"
fi

args=(
  --steelsearch-url "${STEELSEARCH_URL}"
)

REQUIRE_COMPARISON="${REQUIRE_OPENSEARCH_COMPARISON:-${SEARCH_COMPAT_REQUIRE_OPENSEARCH:-0}}"

if [[ "${REQUIRE_COMPARISON}" == "1" && -z "${OPENSEARCH_URL:-}" ]]; then
  echo "OPENSEARCH_URL is required when OpenSearch comparison is mandatory" >&2
  exit 2
fi

if [[ -n "${OPENSEARCH_URL:-}" && ( "${CI:-}" != "true" || "${RUN_OPENSEARCH_COMPARISON:-}" == "1" || "${REQUIRE_COMPARISON}" == "1" ) ]]; then
  args+=(--opensearch-url "${OPENSEARCH_URL}")
elif [[ -n "${OPENSEARCH_URL:-}" && "${CI:-}" == "true" ]]; then
  echo "Skipping OpenSearch comparison in CI; set RUN_OPENSEARCH_COMPARISON=1 to opt in" >&2
fi

previous_arg=""
for arg in "$@"; do
  if [[ "${previous_arg}" == "--fixture" ]]; then
    FIXTURE_PATH="${arg}"
  elif [[ "${previous_arg}" == "--report" ]]; then
    REPORT_PATH="${arg}"
  fi
  previous_arg="${arg}"
done

python3 "${ROOT}/tools/search_compat.py" "${args[@]}" "$@"
python3 "${ROOT}/tools/check-rest-compat-report.py" \
  --fixture "${FIXTURE_PATH}" \
  --report "${REPORT_PATH}" \
  --require-report
