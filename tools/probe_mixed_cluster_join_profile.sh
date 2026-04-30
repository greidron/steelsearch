#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE_PATH="${ROOT_DIR}/tools/fixtures/mixed-cluster-join-admission.json"
WORK_DIR="${PHASE_C_JOIN_WORK_DIR:-${ROOT_DIR}/target/phase-c-mixed-cluster-join}"
RAW_PROBE="${WORK_DIR}/transport-probe.txt"
STATE_JSON="${WORK_DIR}/cluster-state-metadata.json"
NODE_JSON="${WORK_DIR}/node-info.json"
REPORT_PATH="${WORK_DIR}/live-join-probe-report.json"
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

if [[ -z "${OPENSEARCH_BASE_URL:-}" || -z "${OPENSEARCH_TRANSPORT_ADDR:-}" ]]; then
  "${ROOT_DIR}/tools/run-opensearch-dev.sh" >"${WORK_DIR}/opensearch.log" 2>&1 &
  OPENSEARCH_PID=$!
  wait_for_port "${HOST}" "${OPENSEARCH_HTTP_PORT}"
  wait_for_port "${HOST}" "${OPENSEARCH_TRANSPORT_PORT}"
  export OPENSEARCH_BASE_URL="http://${HOST}:${OPENSEARCH_HTTP_PORT}"
  export OPENSEARCH_TRANSPORT_ADDR="${HOST}:${OPENSEARCH_TRANSPORT_PORT}"
fi

cargo run -q -p os-tcp-probe -- --addr "${OPENSEARCH_TRANSPORT_ADDR}" > "${RAW_PROBE}" 2>"${WORK_DIR}/probe.stderr"
curl -fsS "${OPENSEARCH_BASE_URL}/_cluster/state/metadata?local=true" >"${STATE_JSON}"
curl -fsS "${OPENSEARCH_BASE_URL}/_nodes/_local" >"${NODE_JSON}"

python3 - "${FIXTURE_PATH}" "${RAW_PROBE}" "${STATE_JSON}" "${NODE_JSON}" "${REPORT_PATH}" <<'PY'
import json
import sys

fixture_path, raw_probe_path, state_path, node_path, report_path = sys.argv[1:6]
with open(fixture_path, "r", encoding="utf-8") as fh:
    fixture = json.load(fh)
with open(state_path, "r", encoding="utf-8") as fh:
    state = json.load(fh)
with open(node_path, "r", encoding="utf-8") as fh:
    node_info = json.load(fh)

raw = {}
with open(raw_probe_path, "r", encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        raw[key] = value

expected = fixture["join_handshake"]
expected_roles = sorted(role["name"] for role in fixture["discovery_node_advertisement"]["advertised_roles"])
required_attrs = sorted(fixture["discovery_node_advertisement"]["required_attributes"])

nodes = node_info.get("nodes", {})
if len(nodes) != 1:
    local_node = {}
else:
    local_node = next(iter(nodes.values()))

observed_roles = sorted(local_node.get("roles", []))
observed_attrs = sorted((local_node.get("attributes") or {}).keys())
cluster_uuid = (state.get("metadata") or {}).get("cluster_uuid", "")
cluster_name = state.get("cluster_name", "")

checks = {
    "remote_transport_version_matches_fixture": int(raw.get("remote_version_id", -1)) == expected["payload_transport_version_ids"][0],
    "response_header_matches_min_compat": int(raw.get("response_header_version_id", -1)) == expected["minimum_compatible_transport_version_id"],
    "transport_payload_matches_fixture": int(raw.get("transport_version_id", -1)) == expected["payload_transport_version_ids"][0],
    "handshake_cluster_name_matches_state": raw.get("cluster_name", "") == cluster_name,
    "cluster_uuid_present": bool(cluster_uuid),
    "single_local_node_visible": len(nodes) == 1,
    "advertised_roles_match_fixture": observed_roles == expected_roles,
    "required_attributes_present": all(attr in observed_attrs for attr in required_attrs),
    "transport_address_present": bool(local_node.get("transport_address")),
    "node_name_present": bool(local_node.get("name")),
}

report = {
    "fixture": fixture_path,
    "observed": {
        "transport_probe": raw,
        "cluster_name": cluster_name,
        "cluster_uuid": cluster_uuid,
        "node_name": local_node.get("name"),
        "transport_address": local_node.get("transport_address"),
        "roles": observed_roles,
        "attributes": observed_attrs,
    },
    "expected": {
        "payload_transport_version_id": expected["payload_transport_version_ids"][0],
        "minimum_compatible_transport_version_id": expected["minimum_compatible_transport_version_id"],
        "advertised_roles": expected_roles,
        "required_attributes": required_attrs,
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
