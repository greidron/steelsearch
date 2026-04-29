#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT}/docker/docker-compose.replacement.yml"
OUT_DIR="${DOCKER_SCENARIO_DIR:-${ROOT}/target/docker-replacement-scenarios}"
STEELSEARCH_URL="${STEELSEARCH_DOCKER_URL:-http://127.0.0.1:${STEELSEARCH_PORT:-19200}}"
OPENSEARCH_URL="${OPENSEARCH_DOCKER_URL:-http://127.0.0.1:${OPENSEARCH_PORT:-9200}}"
KEEP="${KEEP_DOCKER_SCENARIO:-0}"

compose() {
  docker compose -f "${COMPOSE_FILE}" "$@"
}

wait_url() {
  local name="$1"
  local url="$2"
  local deadline=$((SECONDS + ${DOCKER_SCENARIO_TIMEOUT_SECONDS:-240}))
  until curl -fsS "${url}/" >/dev/null 2>&1; do
    if (( SECONDS >= deadline )); then
      echo "Timed out waiting for ${name} at ${url}" >&2
      return 1
    fi
    sleep 2
  done
}

mode="${1:-full}"
mkdir -p "${OUT_DIR}"

case "${mode}" in
  up|full)
    compose up --build -d
    wait_url "OpenSearch" "${OPENSEARCH_URL}"
    wait_url "Steelsearch" "${STEELSEARCH_URL}"
    ;;
  test|down)
    ;;
  *)
    echo "usage: $0 [full|up|test|down]" >&2
    exit 2
    ;;
esac

if [[ "${mode}" == "full" || "${mode}" == "test" ]]; then
  python3 "${ROOT}/supports/integration_test/docker_replacement_scenarios.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${OUT_DIR}/report.json"
fi

if [[ "${mode}" == "down" || ( "${mode}" == "full" && "${KEEP}" != "1" ) ]]; then
  compose down -v
fi
