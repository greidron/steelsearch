#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${PHASE_B_WORK_DIR:-${ROOT_DIR}/target/phase-b-interop}"
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

run_and_capture_test() {
  local report_path="$1"
  shift
  local test_cmd=("$@")
  local stdout_path="${report_path%.json}.stdout"
  local stderr_path="${report_path%.json}.stderr"
  if "${test_cmd[@]}" >"${stdout_path}" 2>"${stderr_path}"; then
    python3 - "$report_path" "${test_cmd[*]}" <<'PY'
import json
import sys
report_path, command = sys.argv[1:3]
report = {
    "command": command,
    "summary": {
        "passed": True
    }
}
with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY
  else
    cat "${stdout_path}" >&2 || true
    cat "${stderr_path}" >&2 || true
    return 1
  fi
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

PHASE_B_INTEROP_WORK_DIR="${WORK_DIR}/handshake" \
  bash "${ROOT_DIR}/tools/probe_interop_handshake_profile.sh" >"${WORK_DIR}/interop-handshake-report.json"

PHASE_B_CLUSTER_STATE_WORK_DIR="${WORK_DIR}/cluster-state-cache" \
  bash "${ROOT_DIR}/tools/probe_interop_cluster_state_cache_profile.sh" >"${WORK_DIR}/interop-cluster-state-cache-report.json"

PHASE_B_READ_FORWARDING_WORK_DIR="${WORK_DIR}/read-forwarding" \
  bash "${ROOT_DIR}/tools/probe_interop_read_forwarding_profile.sh" >"${WORK_DIR}/interop-read-forwarding-report.json"

PHASE_B_SEARCH_FORWARDING_WORK_DIR="${WORK_DIR}/search-forwarding" \
  bash "${ROOT_DIR}/tools/probe_interop_search_forwarding_profile.sh" >"${WORK_DIR}/interop-search-forwarding-report.json"

run_and_capture_test \
  "${WORK_DIR}/interop-version-gates-report.json" \
  cargo test -p os-core interop_handshake_fixture_matches_current_version_constants -- --nocapture

run_and_capture_test \
  "${WORK_DIR}/interop-custom-metadata-report.json" \
  cargo test -p os-cluster-state interop_unsupported_custom_fixture_cases_reject_and_preserve_prior_cache -- --nocapture

run_and_capture_test \
  "${WORK_DIR}/interop-failure-injection-report.json" \
  cargo test -p os-core interop_failure_injection_ledger_covers_remote_unavailable_and_transport_unwrap --test interop_failure_injection -- --nocapture

if [[ "${STEELSEARCH_JAVA_WRITE_FORWARDING_VALIDATED:-false}" == "true" ]]; then
  PHASE_B_WRITE_FORWARDING_WORK_DIR="${WORK_DIR}/write-forwarding" \
    bash "${ROOT_DIR}/tools/probe_interop_write_forwarding_profile.sh" >"${WORK_DIR}/interop-write-forwarding-report.json"
fi

python3 - "${WORK_DIR}" <<'PY'
import json
import os
import sys

work_dir = sys.argv[1]
report_files = [
    "interop-handshake-report.json",
    "interop-cluster-state-cache-report.json",
    "interop-read-forwarding-report.json",
    "interop-search-forwarding-report.json",
    "interop-version-gates-report.json",
    "interop-custom-metadata-report.json",
    "interop-failure-injection-report.json",
]
optional = ["interop-write-forwarding-report.json"]

reports = {}
passed = True
for name in report_files + optional:
    path = os.path.join(work_dir, name)
    if not os.path.exists(path):
        if name in optional:
            continue
        raise SystemExit(f"missing required report {path}")
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    reports[name] = bool(data.get("summary", {}).get("passed"))
    passed = passed and reports[name]

summary = {
    "work_dir": work_dir,
    "reports": reports,
    "summary": {
        "passed": passed
    }
}
print(json.dumps(summary, indent=2, sort_keys=True))
PY
