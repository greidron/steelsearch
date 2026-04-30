#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE_PATH="${ROOT_DIR}/tools/fixtures/mixed-cluster-allocation-admission.json"
WORK_DIR="${PHASE_C_ALLOCATION_WORK_DIR:-${ROOT_DIR}/target/phase-c-mixed-cluster-allocation}"
STATE_JSON="${WORK_DIR}/routing-state.json"
HEALTH_JSON="${WORK_DIR}/health.json"
REPORT_PATH="${WORK_DIR}/routing-convergence-probe-report.json"
mkdir -p "${WORK_DIR}"

cleanup() {
  if [[ -n "${OPENSEARCH_PID:-}" ]]; then
    kill "${OPENSEARCH_PID}" >/dev/null 2>&1 || true
    wait "${OPENSEARCH_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

wait_for_port() {
  local host="$1"
  local port="$2"
  python3 - "$host" "$port" <<'PY'
import socket
import sys
import time

host = sys.argv[1]
port = int(sys.argv[2])
deadline = time.time() + 120
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=1):
            sys.exit(0)
    except OSError:
        time.sleep(1)
print(f"timed out waiting for {host}:{port}", file=sys.stderr)
sys.exit(1)
PY
}

HOST="${OPENSEARCH_HTTP_HOST:-127.0.0.1}"
OPENSEARCH_HTTP_PORT="${OPENSEARCH_HTTP_PORT:-9200}"
OPENSEARCH_TRANSPORT_PORT="${OPENSEARCH_TRANSPORT_PORT:-9300}"
export OPENSEARCH_HTTP_PORT OPENSEARCH_TRANSPORT_PORT

if [[ -z "${OPENSEARCH_BASE_URL:-}" ]]; then
  "${ROOT_DIR}/tools/run-opensearch-dev.sh" >"${WORK_DIR}/opensearch.log" 2>&1 &
  OPENSEARCH_PID=$!
  wait_for_port "${HOST}" "${OPENSEARCH_HTTP_PORT}"
  export OPENSEARCH_BASE_URL="http://${HOST}:${OPENSEARCH_HTTP_PORT}"
fi

INDEX_NAME="logs-phase-c-000001"
curl -fsS -XDELETE "${OPENSEARCH_BASE_URL}/${INDEX_NAME}?ignore_unavailable=true" >/dev/null
curl -fsS -XPUT "${OPENSEARCH_BASE_URL}/${INDEX_NAME}" \
  -H 'content-type: application/json' \
  -d '{"settings":{"index":{"number_of_shards":1,"number_of_replicas":0}}}' >/dev/null
curl -fsS "${OPENSEARCH_BASE_URL}/_cluster/health/${INDEX_NAME}?wait_for_status=green&timeout=60s" >"${HEALTH_JSON}"
curl -fsS "${OPENSEARCH_BASE_URL}/_cluster/state/metadata,routing_table/${INDEX_NAME}?local=true" >"${STATE_JSON}"

python3 - "${FIXTURE_PATH}" "${HEALTH_JSON}" "${STATE_JSON}" "${REPORT_PATH}" "${INDEX_NAME}" <<'PY'
import fnmatch
import json
import sys

fixture_path, health_path, state_path, report_path, index_name = sys.argv[1:6]
with open(fixture_path, "r", encoding="utf-8") as fh:
    fixture = json.load(fh)
with open(health_path, "r", encoding="utf-8") as fh:
    health = json.load(fh)
with open(state_path, "r", encoding="utf-8") as fh:
    state = json.load(fh)

policy = fixture["allocation_admission_policy"]
patterns = policy["validated_index_family_patterns"]
metadata = state.get("metadata", {}).get("indices", {}).get(index_name, {})
routing_index = state.get("routing_table", {}).get("indices", {}).get(index_name, {})
shards = routing_index.get("shards", {})
shard_zero = shards.get("0", [])
primary = next((item for item in shard_zero if item.get("primary")), {})

checks = {
    "index_matches_validated_family": any(fnmatch.fnmatch(index_name, pattern) for pattern in patterns),
    "cluster_health_green": health.get("status") == "green",
    "metadata_shard_count_is_one": metadata.get("settings", {}).get("index", {}).get("number_of_shards") == "1",
    "metadata_replica_count_is_zero": metadata.get("settings", {}).get("index", {}).get("number_of_replicas") == "0",
    "single_primary_routing_entry": len(shard_zero) == 1 and bool(primary),
    "primary_state_started": primary.get("state") == "STARTED",
    "primary_allocation_id_present": bool((primary.get("allocation_id") or {}).get("id")),
    "primary_search_only_absent_or_false": not primary.get("searchOnly", False),
    "current_node_present": bool(primary.get("node")),
}

report = {
    "fixture": fixture_path,
    "index_name": index_name,
    "observed": {
        "health_status": health.get("status"),
        "metadata_number_of_shards": metadata.get("settings", {}).get("index", {}).get("number_of_shards"),
        "metadata_number_of_replicas": metadata.get("settings", {}).get("index", {}).get("number_of_replicas"),
        "primary_state": primary.get("state"),
        "primary_allocation_id": (primary.get("allocation_id") or {}).get("id"),
        "primary_node": primary.get("node"),
    },
    "checks": checks,
    "summary": {
        "passed": all(checks.values())
    }
}

with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
print(json.dumps(report, indent=2, sort_keys=True))
PY
