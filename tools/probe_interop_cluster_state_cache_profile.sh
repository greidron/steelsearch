#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE_PATH="${ROOT_DIR}/tools/fixtures/interop-cluster-state-cache.json"
WORK_DIR="${PHASE_B_CLUSTER_STATE_WORK_DIR:-${ROOT_DIR}/target/phase-b-interop-cluster-state}"
RAW_OUTPUT="${WORK_DIR}/probe.txt"
REPORT_PATH="${WORK_DIR}/interop-cluster-state-cache-report.json"
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

if [[ -n "${OPENSEARCH_TRANSPORT_ADDR:-}" ]]; then
  TRANSPORT_ADDR="${OPENSEARCH_TRANSPORT_ADDR}"
else
  HOST="${OPENSEARCH_HTTP_HOST:-127.0.0.1}"
  OPENSEARCH_HTTP_PORT="${OPENSEARCH_HTTP_PORT:-9200}"
  OPENSEARCH_TRANSPORT_PORT="${OPENSEARCH_TRANSPORT_PORT:-9300}"
  export OPENSEARCH_HTTP_PORT OPENSEARCH_TRANSPORT_PORT
  "${ROOT_DIR}/tools/run-opensearch-dev.sh" >"${WORK_DIR}/opensearch.log" 2>&1 &
  OPENSEARCH_PID=$!
  wait_for_port "${HOST}" "${OPENSEARCH_TRANSPORT_PORT}"
  TRANSPORT_ADDR="${HOST}:${OPENSEARCH_TRANSPORT_PORT}"
fi

probe_ok=0
for _ in $(seq 1 30); do
  if cargo run -q -p os-tcp-probe -- --addr "${TRANSPORT_ADDR}" --cluster-state-full > "${RAW_OUTPUT}" 2>"${WORK_DIR}/probe.stderr"; then
    probe_ok=1
    break
  fi
  sleep 1
done

if [[ "${probe_ok}" != "1" ]]; then
  cat "${WORK_DIR}/probe.stderr" >&2
  exit 1
fi

python3 - "${FIXTURE_PATH}" "${RAW_OUTPUT}" "${REPORT_PATH}" "${TRANSPORT_ADDR}" <<'PY'
import json
import sys

fixture_path, raw_path, report_path, transport_addr = sys.argv[1:5]
with open(fixture_path, "r", encoding="utf-8") as fh:
    fixture = json.load(fh)

raw = {}
with open(raw_path, "r", encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        raw[key] = value

checks = {}
for key in fixture["required_keys"]:
    checks[f"present:{key}"] = key in raw and raw[key] != ""

for rule in fixture["consistency_checks"]:
    left = rule["left"]
    right = rule["right"]
    checks[f"equal:{left}:{right}"] = raw.get(left) == raw.get(right)

report = {
    "fixture": fixture_path,
    "transport_addr": transport_addr,
    "observed": raw,
    "checks": checks,
    "summary": {
        "passed": all(checks.values())
    }
}

with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY

cat "${REPORT_PATH}"
