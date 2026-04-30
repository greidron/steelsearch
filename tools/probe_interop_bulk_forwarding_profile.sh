#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE_PATH="${ROOT_DIR}/tools/fixtures/interop-bulk-forwarding.json"
WORK_DIR="${PHASE_B_BULK_FORWARDING_WORK_DIR:-${ROOT_DIR}/target/phase-b-interop-bulk-forwarding}"
REPORT_PATH="${WORK_DIR}/interop-bulk-forwarding-report.json"
mkdir -p "${WORK_DIR}"

if [[ "${STEELSEARCH_JAVA_WRITE_FORWARDING_VALIDATED:-false}" != "true" ]]; then
  echo "STEELSEARCH_JAVA_WRITE_FORWARDING_VALIDATED=true is required for Phase B bulk write-forwarding probes" >&2
  exit 1
fi

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

if [[ -n "${OPENSEARCH_BASE_URL:-}" ]]; then
  BASE_URL="${OPENSEARCH_BASE_URL}"
else
  HOST="${OPENSEARCH_HTTP_HOST:-127.0.0.1}"
  OPENSEARCH_HTTP_PORT="${OPENSEARCH_HTTP_PORT:-9200}"
  export OPENSEARCH_HTTP_PORT
  "${ROOT_DIR}/tools/run-opensearch-dev.sh" >"${WORK_DIR}/opensearch.log" 2>&1 &
  OPENSEARCH_PID=$!
  wait_for_port "${HOST}" "${OPENSEARCH_HTTP_PORT}"
  BASE_URL="http://${HOST}:${OPENSEARCH_HTTP_PORT}"
fi

python3 - "${FIXTURE_PATH}" "${BASE_URL}" "${REPORT_PATH}" <<'PY'
import json
import sys
import urllib.request

fixture_path, base_url, report_path = sys.argv[1:4]
with open(fixture_path, "r", encoding="utf-8") as fh:
    fixture = json.load(fh)

index_name = fixture["index"]

def json_request(method, path, body=None):
    data = None
    headers = {"accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["content-type"] = "application/json"
    req = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def bulk_request(body_lines):
    body = ("\n".join(body_lines) + "\n").encode("utf-8")
    req = urllib.request.Request(
        base_url + "/_bulk?refresh=true",
        data=body,
        headers={
            "accept": "application/json",
            "content-type": "application/x-ndjson",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

try:
    json_request("DELETE", f"/{index_name}?ignore_unavailable=true")
except Exception:
    pass
json_request("PUT", f"/{index_name}", {"settings": {"number_of_shards": 1, "number_of_replicas": 0}})

happy_status, happy_body = bulk_request(fixture["happy_path"]["body_lines"])
happy_item_statuses = [next(iter(item.values()))["status"] for item in happy_body["items"]]
happy_checks = {
    "status": happy_status == fixture["happy_path"]["expected_status"],
    "errors": happy_body["errors"] == fixture["happy_path"]["expected_errors"],
    "item_statuses": happy_item_statuses == fixture["happy_path"]["expected_item_statuses"],
}

try:
    json_request("DELETE", f"/{index_name}?ignore_unavailable=true")
except Exception:
    pass
json_request("PUT", f"/{index_name}", {"settings": {"number_of_shards": 1, "number_of_replicas": 0}})

partial_status, partial_body = bulk_request(fixture["partial_failure_policy"]["body_lines"])
partial_checks = {
    "status": partial_status == fixture["partial_failure_policy"]["expected_status"],
    "source_errors": partial_body["errors"] == fixture["partial_failure_policy"]["expected_source_errors"],
    "policy": fixture["partial_failure_policy"]["policy"] == "rejected",
}

report = {
    "fixture": fixture_path,
    "base_url": base_url,
    "gate_required": True,
    "happy_path": {
        "name": fixture["happy_path"]["name"],
        "checks": happy_checks,
        "actual_status": happy_status,
        "actual_errors": happy_body["errors"],
        "actual_item_statuses": happy_item_statuses,
    },
    "partial_failure_policy": {
        "name": fixture["partial_failure_policy"]["name"],
        "checks": partial_checks,
        "actual_status": partial_status,
        "actual_errors": partial_body["errors"],
        "reason": fixture["partial_failure_policy"]["reason"],
    },
}
report["summary"] = {
    "passed": all(happy_checks.values()) and all(partial_checks.values())
}

with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY

cat "${REPORT_PATH}"
