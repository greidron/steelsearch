#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE_PATH="${ROOT_DIR}/tools/fixtures/interop-write-forwarding.json"
WORK_DIR="${PHASE_B_WRITE_FORWARDING_WORK_DIR:-${ROOT_DIR}/target/phase-b-interop-write-forwarding}"
REPORT_PATH="${WORK_DIR}/interop-write-forwarding-report.json"
mkdir -p "${WORK_DIR}"

if [[ "${STEELSEARCH_JAVA_WRITE_FORWARDING_VALIDATED:-false}" != "true" ]]; then
  echo "STEELSEARCH_JAVA_WRITE_FORWARDING_VALIDATED=true is required for Phase B write-forwarding probes" >&2
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

def request(method, path, body=None):
    data = None
    headers = {"accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["content-type"] = "application/json"
    req = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

try:
    request("DELETE", f"/{fixture['index']}?ignore_unavailable=true")
except Exception:
    pass
request("PUT", f"/{fixture['index']}", {"settings": {"number_of_shards": 1, "number_of_replicas": 0}})

cases = []
all_checks = []
for case in fixture["cases"]:
    status, body = request(case["method"], case["path"], case.get("body"))
    actual_result = body.get("result")
    checks = {
        "status": status == case["expected_status"],
        "result": actual_result == case["expected_result"],
    }
    cases.append(
        {
            "name": case["name"],
            "checks": checks,
            "actual_status": status,
            "actual_result": actual_result,
        }
    )
    all_checks.extend(checks.values())

report = {
    "fixture": fixture_path,
    "base_url": base_url,
    "gate_required": True,
    "cases": cases,
    "summary": {
        "passed": all(all_checks),
        "case_count": len(cases),
    },
}

with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY

cat "${REPORT_PATH}"
