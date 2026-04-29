#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT}/docker-compose.rehearsal.yml}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-steelsearch-rehearsal}"
REPORT_DIR="${REPORT_DIR:-${ROOT}/target/docker-replacement-rehearsal}"
STEELSEARCH_URL="${STEELSEARCH_URL:-http://127.0.0.1:${STEELSEARCH_HTTP_PORT:-29201}}"
OPENSEARCH_URL="${OPENSEARCH_URL:-http://127.0.0.1:${OPENSEARCH_HTTP_PORT:-29200}}"
SEARCH_COMPAT_REPORT="${SEARCH_COMPAT_REPORT:-${REPORT_DIR}/search-compat-report.json}"
SCENARIO_REPORT="${SCENARIO_REPORT:-${REPORT_DIR}/docker-replacement-scenarios.json}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-240}"

usage() {
  cat <<'USAGE'
Run the Docker replacement rehearsal.

The rehearsal builds the local Steelsearch image, starts a three-node
Steelsearch cluster and one OpenSearch node with docker compose, then runs:
  1. supported REST/search compatibility checks,
  2. OpenSearch-to-Steelsearch export/import migration rehearsal,
  3. Steelsearch MiniLM-compatible embedding to k-NN search rehearsal.

Environment:
  OPENSEARCH_IMAGE       OpenSearch Docker image. Default: opensearchproject/opensearch:latest
  STEELSEARCH_HTTP_PORT  Host port for steelsearch-1. Default: 29201
  OPENSEARCH_HTTP_PORT   Host port for OpenSearch. Default: 29200
  REPORT_DIR             Output directory. Default: target/docker-replacement-rehearsal
  KEEP_DOCKER_REHEARSAL=1 Leave containers running after completion.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

mkdir -p "${REPORT_DIR}"

cleanup() {
  local status=$?
  if [[ "${KEEP_DOCKER_REHEARSAL:-0}" != "1" ]]; then
    docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" down -v --remove-orphans >/dev/null 2>&1 || true
  else
    echo "KEEP_DOCKER_REHEARSAL=1; containers left running under project ${PROJECT_NAME}" >&2
  fi
  exit "${status}"
}
trap cleanup EXIT INT TERM

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
        with urllib.request.urlopen(url + "/", timeout=3.0) as response:
            if response.status < 500:
                print(f"{name} ready at {url}")
                raise SystemExit(0)
    except Exception as error:  # noqa: BLE001
        last_error = error
    time.sleep(1)
raise SystemExit(f"{name} did not become ready at {url}: {last_error}")
PY
}

cd "${ROOT}"
docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" down -v --remove-orphans >/dev/null 2>&1 || true
docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" build steelsearch-1
docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" up -d

wait_for_endpoint "Steelsearch" "${STEELSEARCH_URL}"
wait_for_endpoint "OpenSearch" "${OPENSEARCH_URL}"

python3 "${ROOT}/tools/search_compat.py" \
  --steelsearch-url "${STEELSEARCH_URL}" \
  --opensearch-url "${OPENSEARCH_URL}" \
  --wait \
  --timeout 30 \
  --report "${SEARCH_COMPAT_REPORT}" || SEARCH_COMPAT_STATUS=$?
SEARCH_COMPAT_STATUS="${SEARCH_COMPAT_STATUS:-0}"

python3 "${ROOT}/supports/integration_test/docker_replacement_scenarios.py" \
  --steelsearch-url "${STEELSEARCH_URL}" \
  --opensearch-url "${OPENSEARCH_URL}" \
  --output "${SCENARIO_REPORT}"

echo "Docker replacement rehearsal reports:"
echo "  search compatibility: ${SEARCH_COMPAT_REPORT} (exit ${SEARCH_COMPAT_STATUS})"
echo "  scenarios: ${SCENARIO_REPORT}"

if [[ "${SEARCH_COMPAT_STATUS}" != "0" ]]; then
  exit "${SEARCH_COMPAT_STATUS}"
fi
