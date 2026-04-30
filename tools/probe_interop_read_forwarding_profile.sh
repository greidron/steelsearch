#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE_PATH="${ROOT_DIR}/tools/fixtures/interop-read-forwarding.json"
WORK_DIR="${PHASE_B_READ_FORWARDING_WORK_DIR:-${ROOT_DIR}/target/phase-b-interop-read-forwarding}"
REPORT_PATH="${WORK_DIR}/interop-read-forwarding-report.json"
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

curl -sS -XDELETE "${BASE_URL}/interop-read-forwarding?ignore_unavailable=true" >/dev/null || true
curl -sS -XPUT "${BASE_URL}/interop-read-forwarding" \
  -H 'content-type: application/json' \
  -d '{"settings":{"number_of_shards":1,"number_of_replicas":0}}' >/dev/null
curl -sS -XPUT "${BASE_URL}/interop-read-forwarding/_doc/doc-1?refresh=true" \
  -H 'content-type: application/json' \
  -d '{"service":"interop","category":"alpha"}' >/dev/null

python3 - "${FIXTURE_PATH}" "${BASE_URL}" "${REPORT_PATH}" <<'PY'
import json
import sys
import urllib.request

fixture_path, base_url, report_path = sys.argv[1:4]

with open(fixture_path, "r", encoding="utf-8") as fh:
    fixture = json.load(fh)

def get_path(value, path):
    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
            continue
        if isinstance(current, list):
            if not part.isdigit():
                return None
            idx = int(part)
            if idx >= len(current):
                return None
            current = current[idx]
            continue
        return None
    return current

cases = []
all_checks = []

for case in fixture["cases"]:
    req = urllib.request.Request(
        base_url + case["path"],
        method=case["method"],
        headers={"accept": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        status = resp.status
        body = json.loads(resp.read().decode("utf-8"))

    checks = {
        "status": status == case["expected_status"],
    }
    for path in case.get("required_paths", []):
        checks[f"present:{path}"] = get_path(body, path) is not None
    for path, expected in case.get("expected_values", {}).items():
        checks[f"equal:{path}"] = get_path(body, path) == expected
    for path, expected_size in case.get("expected_object_sizes", {}).items():
        value = get_path(body, path)
        checks[f"object_size:{path}"] = isinstance(value, dict) and len(value) == expected_size

    cases.append(
        {
            "name": case["name"],
            "path": case["path"],
            "status": status,
            "checks": checks,
        }
    )
    all_checks.extend(checks.values())

report = {
    "fixture": fixture_path,
    "base_url": base_url,
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
