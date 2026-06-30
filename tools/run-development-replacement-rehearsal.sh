#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REHEARSAL_DIR="${REHEARSAL_DIR:-${ROOT}/target/development-replacement-rehearsal}"
REPORT_PATH="${SEARCH_COMPAT_REPORT:-${REHEARSAL_DIR}/search-compat-report.json}"
VALIDATION_REPORT_PATH="${MIGRATION_VALIDATION_REPORT:-${REHEARSAL_DIR}/migration-validation-report.json}"
ROOT_CLUSTER_NODE_COMPAT_REPORT="${ROOT_CLUSTER_NODE_COMPAT_REPORT:-${REHEARSAL_DIR}/root-cluster-node-compat-report.json}"
CLUSTER_HEALTH_COMPAT_REPORT="${CLUSTER_HEALTH_COMPAT_REPORT:-${REHEARSAL_DIR}/cluster-health-compat-report.json}"
ALLOCATION_EXPLAIN_COMPAT_REPORT="${ALLOCATION_EXPLAIN_COMPAT_REPORT:-${REHEARSAL_DIR}/allocation-explain-compat-report.json}"
CLUSTER_SETTINGS_COMPAT_REPORT="${CLUSTER_SETTINGS_COMPAT_REPORT:-${REHEARSAL_DIR}/cluster-settings-compat-report.json}"
CLUSTER_STATE_COMPAT_REPORT="${CLUSTER_STATE_COMPAT_REPORT:-${REHEARSAL_DIR}/cluster-state-compat-report.json}"
TASKS_COMPAT_REPORT="${TASKS_COMPAT_REPORT:-${REHEARSAL_DIR}/tasks-compat-report.json}"
STATS_COMPAT_REPORT="${STATS_COMPAT_REPORT:-${REHEARSAL_DIR}/stats-compat-report.json}"
INDEX_LIFECYCLE_COMPAT_REPORT="${INDEX_LIFECYCLE_COMPAT_REPORT:-${REHEARSAL_DIR}/index-lifecycle-compat-report.json}"
MAPPING_COMPAT_REPORT="${MAPPING_COMPAT_REPORT:-${REHEARSAL_DIR}/mapping-compat-report.json}"
SETTINGS_COMPAT_REPORT="${SETTINGS_COMPAT_REPORT:-${REHEARSAL_DIR}/settings-compat-report.json}"
SINGLE_DOC_CRUD_COMPAT_REPORT="${SINGLE_DOC_CRUD_COMPAT_REPORT:-${REHEARSAL_DIR}/single-doc-crud-compat-report.json}"
REFRESH_COMPAT_REPORT="${REFRESH_COMPAT_REPORT:-${REHEARSAL_DIR}/refresh-compat-report.json}"
BULK_COMPAT_REPORT="${BULK_COMPAT_REPORT:-${REHEARSAL_DIR}/bulk-compat-report.json}"
ROUTING_COMPAT_REPORT="${ROUTING_COMPAT_REPORT:-${REHEARSAL_DIR}/routing-compat-report.json}"
DOCUMENT_WRITE_SEMANTIC_COMPAT_REPORT="${DOCUMENT_WRITE_SEMANTIC_COMPAT_REPORT:-${REHEARSAL_DIR}/document-write-semantic-compat-report.json}"
ALIAS_READ_COMPAT_REPORT="${ALIAS_READ_COMPAT_REPORT:-${REHEARSAL_DIR}/alias-read-compat-report.json}"
TEMPLATE_COMPAT_REPORT="${TEMPLATE_COMPAT_REPORT:-${REHEARSAL_DIR}/template-compat-report.json}"
SNAPSHOT_LIFECYCLE_COMPAT_REPORT="${SNAPSHOT_LIFECYCLE_COMPAT_REPORT:-${REHEARSAL_DIR}/snapshot-lifecycle-compat-report.json}"
DATA_STREAM_ROLLOVER_COMPAT_REPORT="${DATA_STREAM_ROLLOVER_COMPAT_REPORT:-${REHEARSAL_DIR}/data-stream-rollover-compat-report.json}"
MIGRATION_CUTOVER_INTEGRATION_REPORT="${MIGRATION_CUTOVER_INTEGRATION_REPORT:-${REHEARSAL_DIR}/migration-cutover-integration-report.json}"
VECTOR_SEARCH_COMPAT_REPORT="${VECTOR_SEARCH_COMPAT_REPORT:-${REHEARSAL_DIR}/vector-search-compat-report.json}"
KNN_PLUGIN_COMPAT_REPORT="${KNN_PLUGIN_COMPAT_REPORT:-${REHEARSAL_DIR}/knn-plugin-compat-report.json}"
ML_MODEL_SURFACE_COMPAT_REPORT="${ML_MODEL_SURFACE_COMPAT_REPORT:-${REHEARSAL_DIR}/ml-model-surface-compat-report.json}"
ADMIN_OPS_SEMANTIC_COMPAT_REPORT="${ADMIN_OPS_SEMANTIC_COMPAT_REPORT:-${REHEARSAL_DIR}/admin-ops-semantic-report.json}"
MULTI_NODE_TRANSPORT_ADMIN_REPORT="${MULTI_NODE_TRANSPORT_ADMIN_REPORT:-${REHEARSAL_DIR}/multi-node-transport-admin-report.json}"
ALIAS_TEMPLATE_PERSISTENCE_REPORT="${ALIAS_TEMPLATE_PERSISTENCE_REPORT:-${REHEARSAL_DIR}/alias-template-persistence-report.json}"
STEELSEARCH_READINESS_REPORT="${STEELSEARCH_READINESS_REPORT:-${REHEARSAL_DIR}/steelsearch-readiness.json}"
STEELSEARCH_BENCHMARK_REPORT="${STEELSEARCH_BENCHMARK_REPORT:-${REHEARSAL_DIR}/deterministic-baselines.jsonl}"
STEELSEARCH_LOAD_REPORT="${STEELSEARCH_LOAD_REPORT:-${REHEARSAL_DIR}/http-load-baseline.json}"
STEELSEARCH_LOAD_COMPARISON_REPORT="${STEELSEARCH_LOAD_COMPARISON_REPORT:-${REHEARSAL_DIR}/http-load-comparison.json}"
STEELSEARCH_CHAOS_REPORT="${STEELSEARCH_CHAOS_REPORT:-${REHEARSAL_DIR}/chaos-report.json}"
STEELSEARCH_PACKAGING_REPORT="${STEELSEARCH_PACKAGING_REPORT:-${REHEARSAL_DIR}/packaging-report.json}"
STEELSEARCH_ROLLING_UPGRADE_REPORT="${STEELSEARCH_ROLLING_UPGRADE_REPORT:-${REHEARSAL_DIR}/rolling-upgrade-report.json}"
STEELSEARCH_RELEASE_READINESS_FILE="${STEELSEARCH_RELEASE_READINESS_FILE:-${REHEARSAL_DIR}/release-readiness.json}"
STEELSEARCH_RELEASE_EVIDENCE_MAX_AGE_SECONDS="${STEELSEARCH_RELEASE_EVIDENCE_MAX_AGE_SECONDS:-86400}"
WAIT_TIMEOUT="${REHEARSAL_WAIT_TIMEOUT:-300}"
RUN_SEARCH_COMPAT="${RUN_SEARCH_COMPAT:-1}"
PHASE_A_COMPARE_SCOPE="${PHASE_A_COMPARE_SCOPE:-full}"
SNAPSHOT_REPOSITORY_BASE_DIR="${SNAPSHOT_REPOSITORY_BASE_DIR:-}"

STEELSEARCH_STARTED=0
OPENSEARCH_STARTED=0
STEELSEARCH_CLUSTER_STARTED=0
STEELSEARCH_PID=""
OPENSEARCH_PID=""
STEELSEARCH_CLUSTER_PID=""

usage() {
  cat <<'USAGE'
Run a local Steelsearch-vs-OpenSearch development replacement rehearsal.

The rehearsal starts missing local daemons, loads the shared search
compatibility fixture into both targets, compares stable result fields, writes
a migration validation report, and stops the daemons it started.

Environment:
  STEELSEARCH_URL              Reuse an existing Steelsearch endpoint.
  OPENSEARCH_URL               Reuse an existing OpenSearch endpoint.
  STEELSEARCH_HTTP_PORT        Local Steelsearch port when started here. Default: 19201.
  OPENSEARCH_HTTP_PORT         Local OpenSearch port when started here. Default: random free port.
  REHEARSAL_DIR                Output/log directory. Default: target/development-replacement-rehearsal.
  REHEARSAL_WAIT_TIMEOUT       Startup wait timeout in seconds. Default: 300.
  SEARCH_COMPAT_FIXTURE        Fixture passed to tools/search_compat.py.
  SEARCH_COMPAT_REPORT         Search compatibility report path.
  SEARCH_COMPAT_CASES          Comma-separated search compatibility cases.
  KNN_PLUGIN_COMPAT_CASES      Comma-separated k-NN plugin compatibility cases.
  MAPPING_COMPAT_CASES         Comma-separated mapping compatibility cases.
  SNAPSHOT_LIFECYCLE_COMPAT_CASES
                               Comma-separated snapshot lifecycle compatibility cases.
  SNAPSHOT_REPOSITORY_BASE_DIR Snapshot repository fixture base path. Defaults to the local
                               OpenSearch path.repo when this rehearsal starts OpenSearch.
  MIGRATION_VALIDATION_REPORT  Migration validation report path.
  STEELSEARCH_BENCHMARK_REPORT Benchmark JSONL evidence attached to readiness.
  STEELSEARCH_LOAD_REPORT      HTTP load JSON evidence attached to readiness.
  STEELSEARCH_LOAD_COMPARISON_REPORT
                               Steelsearch/OpenSearch load comparison evidence.
  STEELSEARCH_CHAOS_REPORT     Chaos/failure-mode JSON evidence attached to readiness.
  STEELSEARCH_PACKAGING_REPORT Packaging verification JSON evidence attached to readiness.
  STEELSEARCH_ROLLING_UPGRADE_REPORT
                               Rolling-upgrade JSON evidence attached to readiness.
  STEELSEARCH_RELEASE_READINESS_FILE
                               Artifact-backed production startup evidence manifest.
  STEELSEARCH_RELEASE_EVIDENCE_MAX_AGE_SECONDS
                               Max benchmark/load report age. Default: 86400.
  PHASE_A_COMPARE_SCOPE        `full`, `root-cluster-node`, `index-metadata`, `document-write-path`, `search`, `search-execution`, `snapshot-migration`, `vector-ml`, `transport-admin`, or `admin-ops`. Default: full.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

mkdir -p "${REHEARSAL_DIR}"

append_case_args() {
  local raw="${1:-}"
  local -n target_args="$2"
  [[ -n "${raw}" ]] || return 0

  local IFS=","
  local entry trimmed
  local -a entries=()
  read -r -a entries <<< "${raw}"
  for entry in "${entries[@]}"; do
    trimmed="${entry#"${entry%%[![:space:]]*}"}"
    trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"
    [[ -n "${trimmed}" ]] || continue
    target_args+=(--case "${trimmed}")
  done
}

absolute_path() {
  local path="$1"
  if [[ "${path}" == /* ]]; then
    printf '%s\n' "${path}"
  else
    printf '%s/%s\n' "${ROOT}" "${path}"
  fi
}

if [[ "${PHASE_A_COMPARE_SCOPE}" == "root-cluster-node" ]]; then
  RUN_SEARCH_COMPAT=0
  export RUN_INDEX_LIFECYCLE_COMPAT=0
  export RUN_MAPPING_COMPAT=0
  export RUN_SETTINGS_COMPAT=0
  export RUN_SINGLE_DOC_CRUD_COMPAT=0
  export RUN_REFRESH_COMPAT=0
  export RUN_BULK_COMPAT=0
  export RUN_ROUTING_COMPAT=0
  export RUN_ALIAS_READ_COMPAT=0
  export RUN_TEMPLATE_COMPAT=0
  export RUN_SNAPSHOT_LIFECYCLE_COMPAT=0
  export RUN_DATA_STREAM_ROLLOVER_COMPAT=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION=0
  export RUN_VECTOR_SEARCH_COMPAT=0
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=0
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "index-metadata" ]]; then
  RUN_SEARCH_COMPAT=0
  export RUN_CLUSTER_HEALTH_COMPAT=0
  export RUN_ALLOCATION_EXPLAIN_COMPAT=0
  export RUN_CLUSTER_SETTINGS_COMPAT=0
  export RUN_CLUSTER_STATE_COMPAT=0
  export RUN_ROOT_CLUSTER_NODE_COMPAT=0
  export RUN_TASKS_COMPAT=0
  export RUN_STATS_COMPAT=0
  export RUN_SINGLE_DOC_CRUD_COMPAT=0
  export RUN_REFRESH_COMPAT=0
  export RUN_BULK_COMPAT=0
  export RUN_ROUTING_COMPAT=0
  export RUN_SNAPSHOT_LIFECYCLE_COMPAT=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION=0
  export RUN_VECTOR_SEARCH_COMPAT=0
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=0
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "document-write-path" ]]; then
  RUN_SEARCH_COMPAT=0
  export RUN_CLUSTER_HEALTH_COMPAT=0
  export RUN_ALLOCATION_EXPLAIN_COMPAT=0
  export RUN_CLUSTER_SETTINGS_COMPAT=0
  export RUN_CLUSTER_STATE_COMPAT=0
  export RUN_ROOT_CLUSTER_NODE_COMPAT=0
  export RUN_TASKS_COMPAT=0
  export RUN_STATS_COMPAT=0
  export RUN_INDEX_LIFECYCLE_COMPAT=0
  export RUN_MAPPING_COMPAT=0
  export RUN_SETTINGS_COMPAT=0
  export RUN_ALIAS_READ_COMPAT=0
  export RUN_TEMPLATE_COMPAT=0
  export RUN_SNAPSHOT_LIFECYCLE_COMPAT=0
  export RUN_DATA_STREAM_ROLLOVER_COMPAT=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION=0
  export RUN_VECTOR_SEARCH_COMPAT=0
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=0
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "search" ]]; then
  export RUN_CLUSTER_HEALTH_COMPAT=0
  export RUN_ALLOCATION_EXPLAIN_COMPAT=0
  export RUN_CLUSTER_SETTINGS_COMPAT=0
  export RUN_CLUSTER_STATE_COMPAT=0
  export RUN_ROOT_CLUSTER_NODE_COMPAT=0
  export RUN_TASKS_COMPAT=0
  export RUN_STATS_COMPAT=0
  export RUN_INDEX_LIFECYCLE_COMPAT=0
  export RUN_MAPPING_COMPAT=0
  export RUN_SETTINGS_COMPAT=0
  export RUN_SINGLE_DOC_CRUD_COMPAT=0
  export RUN_REFRESH_COMPAT=0
  export RUN_BULK_COMPAT=0
  export RUN_ROUTING_COMPAT=0
  export RUN_ALIAS_READ_COMPAT=0
  export RUN_TEMPLATE_COMPAT=0
  export RUN_SNAPSHOT_LIFECYCLE_COMPAT=0
  export RUN_DATA_STREAM_ROLLOVER_COMPAT=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION=0
  export RUN_VECTOR_SEARCH_COMPAT=0
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=0
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "search-execution" ]]; then
  export RUN_CLUSTER_HEALTH_COMPAT=0
  export RUN_ALLOCATION_EXPLAIN_COMPAT=0
  export RUN_CLUSTER_SETTINGS_COMPAT=0
  export RUN_CLUSTER_STATE_COMPAT=0
  export RUN_ROOT_CLUSTER_NODE_COMPAT=0
  export RUN_TASKS_COMPAT=0
  export RUN_STATS_COMPAT=0
  export RUN_INDEX_LIFECYCLE_COMPAT=0
  export RUN_MAPPING_COMPAT=0
  export RUN_SETTINGS_COMPAT=0
  export RUN_SINGLE_DOC_CRUD_COMPAT=0
  export RUN_REFRESH_COMPAT=0
  export RUN_BULK_COMPAT=0
  export RUN_ROUTING_COMPAT=0
  export RUN_ALIAS_READ_COMPAT=0
  export RUN_TEMPLATE_COMPAT=0
  export RUN_SNAPSHOT_LIFECYCLE_COMPAT=0
  export RUN_DATA_STREAM_ROLLOVER_COMPAT=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION=0
  export RUN_VECTOR_SEARCH_COMPAT=0
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=0
  export SEARCH_COMPAT_FIXTURE="${SEARCH_COMPAT_FIXTURE:-${ROOT}/tools/fixtures/search-execution-compat.json}"
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "full" ]]; then
  export SEARCH_COMPAT_FIXTURE="${SEARCH_COMPAT_FIXTURE:-${ROOT}/tools/fixtures/search-strict-compat.json}"
  export SEARCH_COMPAT_EXCLUDE_CASES="${SEARCH_COMPAT_EXCLUDE_CASES:-get_aliases_readback,cat_count_json,cat_count_text}"
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "snapshot-migration" ]]; then
  RUN_SEARCH_COMPAT=0
  export RUN_CLUSTER_HEALTH_COMPAT=0
  export RUN_ALLOCATION_EXPLAIN_COMPAT=0
  export RUN_CLUSTER_SETTINGS_COMPAT=0
  export RUN_CLUSTER_STATE_COMPAT=0
  export RUN_ROOT_CLUSTER_NODE_COMPAT=0
  export RUN_TASKS_COMPAT=0
  export RUN_STATS_COMPAT=0
  export RUN_INDEX_LIFECYCLE_COMPAT=0
  export RUN_MAPPING_COMPAT=0
  export RUN_SETTINGS_COMPAT=0
  export RUN_SINGLE_DOC_CRUD_COMPAT=0
  export RUN_REFRESH_COMPAT=0
  export RUN_BULK_COMPAT=0
  export RUN_ROUTING_COMPAT=0
  export RUN_ALIAS_READ_COMPAT=0
  export RUN_TEMPLATE_COMPAT=0
  export RUN_DATA_STREAM_ROLLOVER_COMPAT=0
  export RUN_VECTOR_SEARCH_COMPAT=0
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION="${RUN_MIGRATION_CUTOVER_INTEGRATION_SNAPSHOT_PRESET:-1}"
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "vector-ml" ]]; then
  RUN_SEARCH_COMPAT=0
  export RUN_CLUSTER_HEALTH_COMPAT=0
  export RUN_ALLOCATION_EXPLAIN_COMPAT=0
  export RUN_CLUSTER_SETTINGS_COMPAT=0
  export RUN_CLUSTER_STATE_COMPAT=0
  export RUN_ROOT_CLUSTER_NODE_COMPAT=0
  export RUN_TASKS_COMPAT=0
  export RUN_STATS_COMPAT=0
  export RUN_INDEX_LIFECYCLE_COMPAT=0
  export RUN_MAPPING_COMPAT=0
  export RUN_SETTINGS_COMPAT=0
  export RUN_SINGLE_DOC_CRUD_COMPAT=0
  export RUN_REFRESH_COMPAT=0
  export RUN_BULK_COMPAT=0
  export RUN_ROUTING_COMPAT=0
  export RUN_ALIAS_READ_COMPAT=0
  export RUN_TEMPLATE_COMPAT=0
  export RUN_SNAPSHOT_LIFECYCLE_COMPAT=0
  export RUN_DATA_STREAM_ROLLOVER_COMPAT=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION=0
  export RUN_VECTOR_SEARCH_COMPAT=1
  export RUN_KNN_PLUGIN_COMPAT=1
  export RUN_ADMIN_OPS_SEMANTIC_COMPAT=0
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=0
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "transport-admin" ]]; then
  RUN_SEARCH_COMPAT=0
  export RUN_CLUSTER_HEALTH_COMPAT=0
  export RUN_ALLOCATION_EXPLAIN_COMPAT=0
  export RUN_CLUSTER_SETTINGS_COMPAT=0
  export RUN_CLUSTER_STATE_COMPAT=0
  export RUN_ROOT_CLUSTER_NODE_COMPAT=0
  export RUN_TASKS_COMPAT=0
  export RUN_STATS_COMPAT=0
  export RUN_INDEX_LIFECYCLE_COMPAT=0
  export RUN_MAPPING_COMPAT=0
  export RUN_SETTINGS_COMPAT=0
  export RUN_SINGLE_DOC_CRUD_COMPAT=0
  export RUN_REFRESH_COMPAT=0
  export RUN_BULK_COMPAT=0
  export RUN_ROUTING_COMPAT=0
  export RUN_ALIAS_READ_COMPAT=0
  export RUN_TEMPLATE_COMPAT=0
  export RUN_SNAPSHOT_LIFECYCLE_COMPAT=0
  export RUN_DATA_STREAM_ROLLOVER_COMPAT=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION=0
  export RUN_VECTOR_SEARCH_COMPAT=0
  export RUN_ADMIN_OPS_SEMANTIC_COMPAT=0
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=1
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "admin-ops" ]]; then
  RUN_SEARCH_COMPAT=0
  export RUN_CLUSTER_HEALTH_COMPAT=0
  export RUN_ALLOCATION_EXPLAIN_COMPAT=0
  export RUN_CLUSTER_SETTINGS_COMPAT=0
  export RUN_CLUSTER_STATE_COMPAT=0
  export RUN_ROOT_CLUSTER_NODE_COMPAT=0
  export RUN_TASKS_COMPAT=0
  export RUN_STATS_COMPAT=0
  export RUN_INDEX_LIFECYCLE_COMPAT=0
  export RUN_MAPPING_COMPAT=0
  export RUN_SETTINGS_COMPAT=0
  export RUN_SINGLE_DOC_CRUD_COMPAT=0
  export RUN_REFRESH_COMPAT=0
  export RUN_BULK_COMPAT=0
  export RUN_ROUTING_COMPAT=0
  export RUN_ALIAS_READ_COMPAT=0
  export RUN_TEMPLATE_COMPAT=0
  export RUN_SNAPSHOT_LIFECYCLE_COMPAT=0
  export RUN_DATA_STREAM_ROLLOVER_COMPAT=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION=0
  export RUN_VECTOR_SEARCH_COMPAT=0
  export RUN_KNN_PLUGIN_COMPAT=0
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=0
  export RUN_ADMIN_OPS_SEMANTIC_COMPAT=1
fi

cleanup() {
  local status=$?
  if [[ "${status}" != "0" ]]; then
    emit_rehearsal_diagnostics "${status}" || true
  fi
  if [[ "${STEELSEARCH_STARTED}" == "1" && -n "${STEELSEARCH_PID}" ]]; then
    stop_process "Steelsearch" "${STEELSEARCH_PID}"
  fi
  if [[ "${STEELSEARCH_CLUSTER_STARTED}" == "1" && -n "${STEELSEARCH_CLUSTER_PID}" ]]; then
    stop_process "Steelsearch cluster" "${STEELSEARCH_CLUSTER_PID}"
  fi
  if [[ "${OPENSEARCH_STARTED}" == "1" && -n "${OPENSEARCH_PID}" ]]; then
    stop_process "OpenSearch" "${OPENSEARCH_PID}"
  fi
  exit "${status}"
}

emit_rehearsal_diagnostics() {
  local status="$1"
  python3 - "${status}" \
    "${REHEARSAL_DIR}/readiness-timeout-diagnostics.json" \
    "${STEELSEARCH_PID:-}" \
    "${OPENSEARCH_PID:-}" \
    "${STEELSEARCH_URL:-}" \
    "${OPENSEARCH_URL:-}" \
    "${REHEARSAL_DIR}/steelsearch.log" \
    "${REHEARSAL_DIR}/opensearch.log" <<'PY'
import json
import os
import sys
from pathlib import Path

status, report, steel_pid, opensearch_pid, steel_url, opensearch_url, steel_log, opensearch_log = sys.argv[1:]

def process_state(pid: str) -> dict[str, object]:
    if not pid:
        return {"pid": None, "running": False}
    proc = Path("/proc") / pid
    state = {"pid": int(pid), "running": proc.exists()}
    status_path = proc / "status"
    if status_path.exists():
        for line in status_path.read_text(errors="replace").splitlines():
            if line.startswith(("Name:", "State:", "VmRSS:", "Threads:")):
                key, value = line.split(":", 1)
                state[key.lower()] = value.strip()
    return state

def tail(path: str, lines: int = 120) -> list[str]:
    p = Path(path)
    if not p.exists():
        return []
    return p.read_text(errors="replace").splitlines()[-lines:]

payload = {
    "exit_status": int(status),
    "steelsearch": {
        "url": steel_url or None,
        "process": process_state(steel_pid),
        "log": steel_log,
        "log_tail": tail(steel_log),
    },
    "opensearch": {
        "url": opensearch_url or None,
        "process": process_state(opensearch_pid),
        "log": opensearch_log,
        "log_tail": tail(opensearch_log),
    },
}
target = Path(report)
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
print(f"readiness diagnostics report: {target}", file=sys.stderr)
PY
}

stop_process() {
  local name="$1"
  local pid="$2"
  if kill -0 "${pid}" 2>/dev/null; then
    echo "Stopping ${name} pid ${pid}" >&2
    kill "${pid}" 2>/dev/null || true
    wait "${pid}" 2>/dev/null || true
  fi
}

wait_for_endpoint() {
  local name="$1"
  local url="$2"
  python3 - "$name" "$url" "$WAIT_TIMEOUT" <<'PY'
import json
import sys
import time
import urllib.error
import urllib.request

name, url, timeout = sys.argv[1], sys.argv[2].rstrip("/"), float(sys.argv[3])
deadline = time.monotonic() + timeout
last_error = None
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(url + "/", timeout=2.0) as response:
            if response.status < 500:
                print(f"{name} is ready at {url}", file=sys.stderr)
                raise SystemExit(0)
    except Exception as error:  # noqa: BLE001
        last_error = error
    time.sleep(0.5)
raise SystemExit(f"{name} did not become ready at {url}: {last_error}")
PY
}

find_free_port() {
  local host="$1"
  python3 - "$host" <<'PY'
import socket
import sys

host = sys.argv[1]
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind((host, 0))
    print(sock.getsockname()[1])
PY
}

capture_steelsearch_readiness() {
  local url="$1"
  python3 - "$url" "$STEELSEARCH_READINESS_REPORT" <<'PY' || true
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

url, report = sys.argv[1].rstrip("/"), Path(sys.argv[2])
try:
    with urllib.request.urlopen(url + "/_steelsearch/readiness", timeout=5.0) as response:
        payload = json.loads(response.read().decode("utf-8"))
except Exception as error:  # noqa: BLE001
    payload = {"available": False, "error": str(error)}
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"Steelsearch readiness report: {report}", file=sys.stderr)
PY
}

attach_release_evidence_to_readiness() {
  python3 "${ROOT}/tools/attach-release-readiness-evidence.py" \
    --readiness-report "${STEELSEARCH_READINESS_REPORT}" \
    --benchmark-report "${STEELSEARCH_BENCHMARK_REPORT}" \
    --load-report "${STEELSEARCH_LOAD_REPORT}" \
    --load-comparison-report "${STEELSEARCH_LOAD_COMPARISON_REPORT}" \
    --chaos-report "${STEELSEARCH_CHAOS_REPORT}" \
    --packaging-report "${STEELSEARCH_PACKAGING_REPORT}" \
    --rolling-upgrade-report "${STEELSEARCH_ROLLING_UPGRADE_REPORT}" \
    --release-readiness-file "${STEELSEARCH_RELEASE_READINESS_FILE}" \
    --max-age-seconds "${STEELSEARCH_RELEASE_EVIDENCE_MAX_AGE_SECONDS}"
}

validate_migration_report() {
  python3 - "$REPORT_PATH" "$VALIDATION_REPORT_PATH" <<'PY'
import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
report = json.loads(source.read_text(encoding="utf-8"))
blockers = []

targets = report.get("targets", {})
if "steelsearch" not in targets:
    blockers.append("missing steelsearch target")
if "opensearch" not in targets:
    blockers.append("missing opensearch target")

for step in report.get("setup", []):
    status = step.get("status")
    if status == "passed":
        continue
    if status == "skipped" and (step.get("skip_scope") or step.get("skipped_reason")):
        continue
    blockers.append(f"setup:{step.get('target')}:{step.get('name')}")

for case in report.get("cases", []):
    status = case.get("status")
    if status == "passed":
        continue
    if status == "skipped" and (case.get("skip_scope") or case.get("skipped_reason")):
        continue
    blockers.append(f"case:{case.get('name')}:{status or 'unknown_status'}")

summary = report.get("summary", {})
if summary.get("failed", 0):
    blockers.append(f"summary.failed:{summary.get('failed')}")

validation = {
    "ready": not blockers,
    "source_report": str(source),
    "targets": targets,
    "checked_setup_steps": len(report.get("setup", [])),
    "checked_cases": len(report.get("cases", [])),
    "blockers": sorted(set(blockers)),
}
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"migration validation ready: {str(validation['ready']).lower()}")
print(f"migration validation report: {target}")
if blockers:
    raise SystemExit(1)
PY
}

trap cleanup EXIT INT TERM

if [[ "${RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION:-0}" == "1" && -z "${STEELSEARCH_NODE_A_URL:-}" && -z "${STEELSEARCH_NODE_B_URL:-}" ]]; then
  export STEELSEARCH_CLUSTER_WORK_DIR="${STEELSEARCH_CLUSTER_WORK_DIR:-${REHEARSAL_DIR}/steelsearch-cluster}"
  export STEELSEARCH_NODE_COUNT="${STEELSEARCH_NODE_COUNT:-2}"
  rm -rf "${STEELSEARCH_CLUSTER_WORK_DIR}"
  echo "Starting Steelsearch cluster for multi-node transport/admin integration" >&2
  "${ROOT}/tools/run-steelsearch-cluster-dev.sh" >"${REHEARSAL_DIR}/steelsearch-cluster.log" 2>&1 &
  STEELSEARCH_CLUSTER_PID=$!
  STEELSEARCH_CLUSTER_STARTED=1
  CLUSTER_MANIFEST="${STEELSEARCH_CLUSTER_WORK_DIR}/cluster.json"
  for _ in {1..120}; do
    if [[ -f "${CLUSTER_MANIFEST}" ]]; then
      break
    fi
    sleep 0.25
  done
  if [[ ! -f "${CLUSTER_MANIFEST}" ]]; then
    echo "Steelsearch cluster manifest was not created at ${CLUSTER_MANIFEST}" >&2
    exit 1
  fi
  readarray -t cluster_urls < <(python3 - "${CLUSTER_MANIFEST}" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for node in manifest.get("nodes", [])[:2]:
    print(node["http_url"])
PY
)
  if [[ "${#cluster_urls[@]}" -lt 2 ]]; then
    echo "Steelsearch cluster manifest did not expose two node URLs" >&2
    exit 1
  fi
  export STEELSEARCH_NODE_A_URL="${STEELSEARCH_NODE_A_URL:-${cluster_urls[0]}}"
  export STEELSEARCH_NODE_B_URL="${STEELSEARCH_NODE_B_URL:-${cluster_urls[1]}}"
  for cluster_url in "${STEELSEARCH_NODE_A_URL}" "${STEELSEARCH_NODE_B_URL}"; do
    ready=0
    for _ in $(seq 1 "$((WAIT_TIMEOUT * 4))"); do
      if curl -fsS "${cluster_url%/}/_steelsearch/dev/cluster" >/dev/null 2>&1; then
        ready=1
        break
      fi
      sleep 0.25
    done
    if [[ "${ready}" != "1" ]]; then
      echo "Steelsearch cluster node did not become ready at ${cluster_url}" >&2
      exit 1
    fi
  done
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" != "transport-admin" ]]; then
  if [[ -n "${OPENSEARCH_URL:-}" ]]; then
    SNAPSHOT_REPOSITORY_BASE_DIR="$(absolute_path "${SNAPSHOT_REPOSITORY_BASE_DIR:-${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}/build/testclusters/runTask-0/repo}")"
    export SNAPSHOT_REPOSITORY_BASE_DIR
  else
    OPENSEARCH_WORK_DIR="$(absolute_path "${OPENSEARCH_WORK_DIR:-${REHEARSAL_DIR}/opensearch}")"
    export OPENSEARCH_WORK_DIR
    OPENSEARCH_REPO_DIR="$(absolute_path "${OPENSEARCH_REPO_DIR:-${OPENSEARCH_WORK_DIR}/repo}")"
    export OPENSEARCH_REPO_DIR
    SNAPSHOT_REPOSITORY_BASE_DIR="$(absolute_path "${SNAPSHOT_REPOSITORY_BASE_DIR:-${OPENSEARCH_REPO_DIR}}")"
    export SNAPSHOT_REPOSITORY_BASE_DIR
  fi
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" != "transport-admin" && -n "${STEELSEARCH_URL:-}" ]]; then
  STEELSEARCH_URL="${STEELSEARCH_URL%/}"
  echo "Using existing Steelsearch endpoint: ${STEELSEARCH_URL}" >&2
elif [[ "${PHASE_A_COMPARE_SCOPE}" != "transport-admin" ]]; then
  STEELSEARCH_HTTP_HOST="${STEELSEARCH_HTTP_HOST:-127.0.0.1}"
  STEELSEARCH_HTTP_PORT="${STEELSEARCH_HTTP_PORT:-19201}"
  STEELSEARCH_TRANSPORT_PORT="${STEELSEARCH_TRANSPORT_PORT:-19301}"
  STEELSEARCH_URL="http://${STEELSEARCH_HTTP_HOST}:${STEELSEARCH_HTTP_PORT}"
  export STEELSEARCH_HTTP_HOST STEELSEARCH_HTTP_PORT STEELSEARCH_TRANSPORT_PORT
  export STEELSEARCH_WORK_DIR="${STEELSEARCH_WORK_DIR:-${REHEARSAL_DIR}/steelsearch}"
  rm -f "${REHEARSAL_DIR}/shared-runtime-state.json"
  rm -rf "${STEELSEARCH_WORK_DIR}"
  echo "Starting Steelsearch at ${STEELSEARCH_URL}" >&2
  "${ROOT}/tools/run-steelsearch-dev.sh" >"${REHEARSAL_DIR}/steelsearch.log" 2>&1 &
  STEELSEARCH_PID=$!
  STEELSEARCH_STARTED=1
fi
if [[ "${PHASE_A_COMPARE_SCOPE}" != "transport-admin" ]]; then
  export STEELSEARCH_URL
  wait_for_endpoint "Steelsearch" "${STEELSEARCH_URL}"
  capture_steelsearch_readiness "${STEELSEARCH_URL}"
  attach_release_evidence_to_readiness
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" != "transport-admin" && "${PHASE_A_COMPARE_SCOPE}" != "admin-ops" && -n "${OPENSEARCH_URL:-}" ]]; then
  OPENSEARCH_URL="${OPENSEARCH_URL%/}"
  echo "Using existing OpenSearch endpoint: ${OPENSEARCH_URL}" >&2
elif [[ "${PHASE_A_COMPARE_SCOPE}" != "transport-admin" && "${PHASE_A_COMPARE_SCOPE}" != "admin-ops" ]]; then
  OPENSEARCH_HTTP_HOST="${OPENSEARCH_HTTP_HOST:-127.0.0.1}"
  OPENSEARCH_HTTP_PORT="${OPENSEARCH_HTTP_PORT:-9200}"
  OPENSEARCH_URL="http://${OPENSEARCH_HTTP_HOST}:${OPENSEARCH_HTTP_PORT}"
  export OPENSEARCH_HTTP_HOST OPENSEARCH_HTTP_PORT
  rm -rf "${OPENSEARCH_WORK_DIR}"
  echo "Starting OpenSearch at ${OPENSEARCH_URL}" >&2
  if [[ "${PHASE_A_COMPARE_SCOPE}" == "vector-ml" ]]; then
    "${ROOT}/tools/run-opensearch-vector-dev.sh" >"${REHEARSAL_DIR}/opensearch.log" 2>&1 &
  else
    "${ROOT}/tools/run-opensearch-dev.sh" >"${REHEARSAL_DIR}/opensearch.log" 2>&1 &
  fi
  OPENSEARCH_PID=$!
  OPENSEARCH_STARTED=1
fi
if [[ "${PHASE_A_COMPARE_SCOPE}" != "transport-admin" && "${PHASE_A_COMPARE_SCOPE}" != "admin-ops" ]]; then
  export OPENSEARCH_URL
  wait_for_endpoint "OpenSearch" "${OPENSEARCH_URL}"
  export REQUIRE_OPENSEARCH_COMPARISON=1
fi

if [[ "${RUN_CLUSTER_HEALTH_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/cluster_health_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${CLUSTER_HEALTH_COMPAT_REPORT}"
fi
if [[ "${RUN_ALLOCATION_EXPLAIN_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/allocation_explain_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${ALLOCATION_EXPLAIN_COMPAT_REPORT}"
fi
if [[ "${RUN_CLUSTER_SETTINGS_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/cluster_settings_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${CLUSTER_SETTINGS_COMPAT_REPORT}"
fi
if [[ "${RUN_CLUSTER_STATE_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/cluster_state_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${CLUSTER_STATE_COMPAT_REPORT}"
fi
if [[ "${RUN_ROOT_CLUSTER_NODE_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/root_cluster_node_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${ROOT_CLUSTER_NODE_COMPAT_REPORT}"
fi
if [[ "${RUN_TASKS_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/tasks_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${TASKS_COMPAT_REPORT}"
fi
if [[ "${RUN_STATS_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/stats_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${STATS_COMPAT_REPORT}"
fi
if [[ "${RUN_INDEX_LIFECYCLE_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/index_lifecycle_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${INDEX_LIFECYCLE_COMPAT_REPORT}"
fi
if [[ "${RUN_MAPPING_COMPAT:-1}" == "1" ]]; then
  mapping_args=(
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${MAPPING_COMPAT_REPORT}"
  )
  append_case_args "${MAPPING_COMPAT_CASES:-}" mapping_args
  python3 "${ROOT}/tools/mapping_compat.py" "${mapping_args[@]}"
fi
if [[ "${RUN_SETTINGS_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/settings_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${SETTINGS_COMPAT_REPORT}"
fi
if [[ "${RUN_SINGLE_DOC_CRUD_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/single_doc_crud_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${SINGLE_DOC_CRUD_COMPAT_REPORT}"
fi
if [[ "${RUN_REFRESH_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/refresh_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${REFRESH_COMPAT_REPORT}"
fi
if [[ "${RUN_BULK_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/bulk_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${BULK_COMPAT_REPORT}"
fi
if [[ "${RUN_ROUTING_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/routing_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${ROUTING_COMPAT_REPORT}"
fi
if [[ "${RUN_DOCUMENT_WRITE_SEMANTIC_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/search_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --fixture "${ROOT}/tools/fixtures/document-write-semantic-compat.json" \
    --report "${DOCUMENT_WRITE_SEMANTIC_COMPAT_REPORT}" \
    --wait \
    --timeout "${SEARCH_COMPAT_TIMEOUT:-10}"
fi
if [[ "${RUN_ALIAS_READ_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/alias_read_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${ALIAS_READ_COMPAT_REPORT}"
fi
if [[ "${RUN_TEMPLATE_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/template_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${TEMPLATE_COMPAT_REPORT}"
fi
if [[ "${RUN_SNAPSHOT_LIFECYCLE_COMPAT:-1}" == "1" ]]; then
  snapshot_lifecycle_args=(
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${SNAPSHOT_LIFECYCLE_COMPAT_REPORT}"
  )
  append_case_args "${SNAPSHOT_LIFECYCLE_COMPAT_CASES:-}" snapshot_lifecycle_args
  python3 "${ROOT}/tools/snapshot_lifecycle_compat.py" "${snapshot_lifecycle_args[@]}"
fi
if [[ "${RUN_DATA_STREAM_ROLLOVER_COMPAT:-1}" == "1" ]]; then
  python3 "${ROOT}/tools/data_stream_rollover_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${DATA_STREAM_ROLLOVER_COMPAT_REPORT}"
fi
if [[ "${RUN_MIGRATION_CUTOVER_INTEGRATION:-0}" == "1" ]]; then
  python3 "${ROOT}/tools/migration_cutover_integration.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${MIGRATION_CUTOVER_INTEGRATION_REPORT}"
fi
if [[ "${RUN_VECTOR_SEARCH_COMPAT:-0}" == "1" ]]; then
  python3 "${ROOT}/tools/vector_search_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${VECTOR_SEARCH_COMPAT_REPORT}"
fi
if [[ "${RUN_KNN_PLUGIN_COMPAT:-0}" == "1" ]]; then
  knn_plugin_cases="${KNN_PLUGIN_COMPAT_CASES:-knn_settings_readback,knn_warmup_basic_shape,knn_clear_cache_basic_shape,knn_model_lifecycle_shape,knn_warmup_budget_failure,knn_warmup_clear_cache_telemetry_shape}"
  knn_plugin_args=(
    --steelsearch-url "${STEELSEARCH_URL}"
    --report "${KNN_PLUGIN_COMPAT_REPORT}"
    --wait
    --timeout "${SEARCH_COMPAT_TIMEOUT:-10}"
  )
  append_case_args "${knn_plugin_cases}" knn_plugin_args
  OPENSEARCH_URL= python3 "${ROOT}/tools/search_compat.py" "${knn_plugin_args[@]}"
  python3 "${ROOT}/tools/check-rest-compat-report.py" \
    --fixture "${ROOT}/tools/fixtures/search-compat.json" \
    --report "${KNN_PLUGIN_COMPAT_REPORT}" \
    --require-report \
    --allow-partial-report
fi
if [[ "${RUN_ML_MODEL_SURFACE_COMPAT:-0}" == "1" ]]; then
  python3 "${ROOT}/tools/ml_model_surface_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --output "${ML_MODEL_SURFACE_COMPAT_REPORT}"
fi
if [[ "${RUN_ADMIN_OPS_SEMANTIC_COMPAT:-0}" == "1" ]]; then
  OPENSEARCH_URL= python3 "${ROOT}/tools/search_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --fixture "${ROOT}/tools/fixtures/admin-ops-semantic-compat.json" \
    --report "${ADMIN_OPS_SEMANTIC_COMPAT_REPORT}" \
    --wait \
    --timeout "${SEARCH_COMPAT_TIMEOUT:-10}"
fi
if [[ "${RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION:-0}" == "1" ]]; then
  python3 "${ROOT}/tools/multi_node_transport_admin_integration.py" \
    --node-a-url "${STEELSEARCH_NODE_A_URL}" \
    --node-b-url "${STEELSEARCH_NODE_B_URL}" \
    --output "${MULTI_NODE_TRANSPORT_ADMIN_REPORT}"
fi
if [[ "${RUN_ALIAS_TEMPLATE_PERSISTENCE_COMPARISON:-0}" == "1" ]]; then
  python3 "${ROOT}/tools/alias_template_persistence_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${ALIAS_TEMPLATE_PERSISTENCE_REPORT}"
fi
if [[ "${RUN_SEARCH_COMPAT}" == "1" ]]; then
  compat_args=(--report "${REPORT_PATH}" --wait --timeout "${SEARCH_COMPAT_TIMEOUT:-10}")
  if [[ -n "${SEARCH_COMPAT_FIXTURE:-}" ]]; then
    compat_args+=(--fixture "${SEARCH_COMPAT_FIXTURE}")
  fi
  append_case_args "${SEARCH_COMPAT_CASES:-}" compat_args

  "${ROOT}/tools/run-search-compat.sh" "${compat_args[@]}"
fi
if [[ "${RUN_SEARCH_COMPAT}" == "1" && "${PHASE_A_COMPARE_SCOPE}" != "search" && "${PHASE_A_COMPARE_SCOPE}" != "snapshot-migration" && "${PHASE_A_COMPARE_SCOPE}" != "vector-ml" && "${PHASE_A_COMPARE_SCOPE}" != "transport-admin" ]]; then
  validate_migration_report
fi

echo "development replacement rehearsal completed"
if [[ "${RUN_SEARCH_COMPAT}" == "1" ]]; then
  echo "search compatibility report: ${REPORT_PATH}"
fi
if [[ "${RUN_CLUSTER_HEALTH_COMPAT:-1}" == "1" ]]; then
  echo "cluster health compatibility report: ${CLUSTER_HEALTH_COMPAT_REPORT}"
fi
if [[ "${RUN_ALLOCATION_EXPLAIN_COMPAT:-1}" == "1" ]]; then
  echo "allocation explain compatibility report: ${ALLOCATION_EXPLAIN_COMPAT_REPORT}"
fi
if [[ "${RUN_CLUSTER_SETTINGS_COMPAT:-1}" == "1" ]]; then
  echo "cluster settings compatibility report: ${CLUSTER_SETTINGS_COMPAT_REPORT}"
fi
if [[ "${RUN_CLUSTER_STATE_COMPAT:-1}" == "1" ]]; then
  echo "cluster state compatibility report: ${CLUSTER_STATE_COMPAT_REPORT}"
fi
if [[ "${RUN_ROOT_CLUSTER_NODE_COMPAT:-1}" == "1" ]]; then
  echo "root/cluster/node compatibility report: ${ROOT_CLUSTER_NODE_COMPAT_REPORT}"
fi
if [[ "${RUN_TASKS_COMPAT:-1}" == "1" ]]; then
  echo "task/pending-task compatibility report: ${TASKS_COMPAT_REPORT}"
fi
if [[ "${RUN_STATS_COMPAT:-1}" == "1" ]]; then
  echo "stats compatibility report: ${STATS_COMPAT_REPORT}"
fi
if [[ "${RUN_INDEX_LIFECYCLE_COMPAT:-1}" == "1" ]]; then
  echo "index lifecycle compatibility report: ${INDEX_LIFECYCLE_COMPAT_REPORT}"
fi
if [[ "${RUN_MAPPING_COMPAT:-1}" == "1" ]]; then
  echo "mapping compatibility report: ${MAPPING_COMPAT_REPORT}"
fi
if [[ "${RUN_SETTINGS_COMPAT:-1}" == "1" ]]; then
  echo "settings compatibility report: ${SETTINGS_COMPAT_REPORT}"
fi
if [[ "${RUN_SINGLE_DOC_CRUD_COMPAT:-1}" == "1" ]]; then
  echo "single-document CRUD compatibility report: ${SINGLE_DOC_CRUD_COMPAT_REPORT}"
fi
if [[ "${RUN_REFRESH_COMPAT:-1}" == "1" ]]; then
  echo "refresh compatibility report: ${REFRESH_COMPAT_REPORT}"
fi
if [[ "${RUN_BULK_COMPAT:-1}" == "1" ]]; then
  echo "bulk compatibility report: ${BULK_COMPAT_REPORT}"
fi
if [[ "${RUN_ROUTING_COMPAT:-1}" == "1" ]]; then
  echo "routing compatibility report: ${ROUTING_COMPAT_REPORT}"
fi
if [[ "${RUN_DOCUMENT_WRITE_SEMANTIC_COMPAT:-1}" == "1" ]]; then
  echo "document write semantic compatibility report: ${DOCUMENT_WRITE_SEMANTIC_COMPAT_REPORT}"
fi
if [[ "${RUN_ALIAS_READ_COMPAT:-1}" == "1" ]]; then
  echo "alias read compatibility report: ${ALIAS_READ_COMPAT_REPORT}"
fi
if [[ "${RUN_TEMPLATE_COMPAT:-1}" == "1" ]]; then
  echo "template compatibility report: ${TEMPLATE_COMPAT_REPORT}"
fi
if [[ "${RUN_SNAPSHOT_LIFECYCLE_COMPAT:-1}" == "1" ]]; then
  echo "snapshot lifecycle compatibility report: ${SNAPSHOT_LIFECYCLE_COMPAT_REPORT}"
fi
if [[ "${RUN_DATA_STREAM_ROLLOVER_COMPAT:-1}" == "1" ]]; then
  echo "data stream/rollover compatibility report: ${DATA_STREAM_ROLLOVER_COMPAT_REPORT}"
fi
if [[ "${RUN_MIGRATION_CUTOVER_INTEGRATION:-0}" == "1" ]]; then
  echo "migration/cutover integration report: ${MIGRATION_CUTOVER_INTEGRATION_REPORT}"
fi
if [[ "${RUN_VECTOR_SEARCH_COMPAT:-0}" == "1" ]]; then
  echo "vector search compatibility report: ${VECTOR_SEARCH_COMPAT_REPORT}"
fi
if [[ "${RUN_KNN_PLUGIN_COMPAT:-0}" == "1" ]]; then
  echo "k-NN plugin compatibility report: ${KNN_PLUGIN_COMPAT_REPORT}"
fi
if [[ "${RUN_ML_MODEL_SURFACE_COMPAT:-0}" == "1" ]]; then
  echo "ml model surface compatibility report: ${ML_MODEL_SURFACE_COMPAT_REPORT}"
fi
if [[ "${RUN_ADMIN_OPS_SEMANTIC_COMPAT:-0}" == "1" ]]; then
  echo "admin ops semantic compatibility report: ${ADMIN_OPS_SEMANTIC_COMPAT_REPORT}"
fi
if [[ "${RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION:-0}" == "1" ]]; then
  echo "multi-node transport/admin integration report: ${MULTI_NODE_TRANSPORT_ADMIN_REPORT}"
fi
if [[ "${RUN_ALIAS_TEMPLATE_PERSISTENCE_COMPARISON:-0}" == "1" ]]; then
  echo "alias/template persistence report: ${ALIAS_TEMPLATE_PERSISTENCE_REPORT}"
fi
if [[ "${PHASE_A_COMPARE_SCOPE}" != "search" && "${PHASE_A_COMPARE_SCOPE}" != "snapshot-migration" && "${PHASE_A_COMPARE_SCOPE}" != "vector-ml" && "${PHASE_A_COMPARE_SCOPE}" != "transport-admin" && "${PHASE_A_COMPARE_SCOPE}" != "admin-ops" ]]; then
  echo "migration validation report: ${VALIDATION_REPORT_PATH}"
fi
