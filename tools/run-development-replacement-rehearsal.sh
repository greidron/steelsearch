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
ALIAS_READ_COMPAT_REPORT="${ALIAS_READ_COMPAT_REPORT:-${REHEARSAL_DIR}/alias-read-compat-report.json}"
TEMPLATE_COMPAT_REPORT="${TEMPLATE_COMPAT_REPORT:-${REHEARSAL_DIR}/template-compat-report.json}"
SNAPSHOT_LIFECYCLE_COMPAT_REPORT="${SNAPSHOT_LIFECYCLE_COMPAT_REPORT:-${REHEARSAL_DIR}/snapshot-lifecycle-compat-report.json}"
DATA_STREAM_ROLLOVER_COMPAT_REPORT="${DATA_STREAM_ROLLOVER_COMPAT_REPORT:-${REHEARSAL_DIR}/data-stream-rollover-compat-report.json}"
MIGRATION_CUTOVER_INTEGRATION_REPORT="${MIGRATION_CUTOVER_INTEGRATION_REPORT:-${REHEARSAL_DIR}/migration-cutover-integration-report.json}"
VECTOR_SEARCH_COMPAT_REPORT="${VECTOR_SEARCH_COMPAT_REPORT:-${REHEARSAL_DIR}/vector-search-compat-report.json}"
MULTI_NODE_TRANSPORT_ADMIN_REPORT="${MULTI_NODE_TRANSPORT_ADMIN_REPORT:-${REHEARSAL_DIR}/multi-node-transport-admin-report.json}"
STEELSEARCH_READINESS_REPORT="${STEELSEARCH_READINESS_REPORT:-${REHEARSAL_DIR}/steelsearch-readiness.json}"
STEELSEARCH_BENCHMARK_REPORT="${STEELSEARCH_BENCHMARK_REPORT:-${REHEARSAL_DIR}/deterministic-baselines.jsonl}"
STEELSEARCH_LOAD_REPORT="${STEELSEARCH_LOAD_REPORT:-${REHEARSAL_DIR}/http-load-baseline.json}"
STEELSEARCH_LOAD_COMPARISON_REPORT="${STEELSEARCH_LOAD_COMPARISON_REPORT:-${REHEARSAL_DIR}/http-load-comparison.json}"
STEELSEARCH_RELEASE_EVIDENCE_MAX_AGE_SECONDS="${STEELSEARCH_RELEASE_EVIDENCE_MAX_AGE_SECONDS:-86400}"
WAIT_TIMEOUT="${REHEARSAL_WAIT_TIMEOUT:-300}"
RUN_SEARCH_COMPAT="${RUN_SEARCH_COMPAT:-1}"
PHASE_A_COMPARE_SCOPE="${PHASE_A_COMPARE_SCOPE:-full}"

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
  MIGRATION_VALIDATION_REPORT  Migration validation report path.
  STEELSEARCH_BENCHMARK_REPORT Benchmark JSONL evidence attached to readiness.
  STEELSEARCH_LOAD_REPORT      HTTP load JSON evidence attached to readiness.
  STEELSEARCH_LOAD_COMPARISON_REPORT
                               Steelsearch/OpenSearch load comparison evidence.
  STEELSEARCH_RELEASE_EVIDENCE_MAX_AGE_SECONDS
                               Max benchmark/load report age. Default: 86400.
  PHASE_A_COMPARE_SCOPE        `full`, `root-cluster-node`, `index-metadata`, `document-write-path`, `search`, `snapshot-migration`, `vector-ml`, or `transport-admin`. Default: full.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

mkdir -p "${REHEARSAL_DIR}"

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
  export RUN_MIGRATION_CUTOVER_INTEGRATION=1
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
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=1
fi

cleanup() {
  local status=$?
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

if [[ "${PHASE_A_COMPARE_SCOPE}" != "transport-admin" && -n "${OPENSEARCH_URL:-}" ]]; then
  OPENSEARCH_URL="${OPENSEARCH_URL%/}"
  echo "Using existing OpenSearch endpoint: ${OPENSEARCH_URL}" >&2
elif [[ "${PHASE_A_COMPARE_SCOPE}" != "transport-admin" ]]; then
  OPENSEARCH_HTTP_HOST="${OPENSEARCH_HTTP_HOST:-127.0.0.1}"
  OPENSEARCH_HTTP_PORT="${OPENSEARCH_HTTP_PORT:-9200}"
  OPENSEARCH_URL="http://${OPENSEARCH_HTTP_HOST}:${OPENSEARCH_HTTP_PORT}"
  export OPENSEARCH_HTTP_HOST OPENSEARCH_HTTP_PORT
  export OPENSEARCH_WORK_DIR="${OPENSEARCH_WORK_DIR:-${REHEARSAL_DIR}/opensearch}"
  rm -rf "${OPENSEARCH_WORK_DIR}"
  echo "Starting OpenSearch at ${OPENSEARCH_URL}" >&2
  "${ROOT}/tools/run-opensearch-dev.sh" >"${REHEARSAL_DIR}/opensearch.log" 2>&1 &
  OPENSEARCH_PID=$!
  OPENSEARCH_STARTED=1
fi
if [[ "${PHASE_A_COMPARE_SCOPE}" != "transport-admin" ]]; then
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
  python3 "${ROOT}/tools/mapping_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${MAPPING_COMPAT_REPORT}"
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
  python3 "${ROOT}/tools/snapshot_lifecycle_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL}" \
    --opensearch-url "${OPENSEARCH_URL}" \
    --output "${SNAPSHOT_LIFECYCLE_COMPAT_REPORT}"
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
if [[ "${RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION:-0}" == "1" ]]; then
  python3 "${ROOT}/tools/multi_node_transport_admin_integration.py" \
    --node-a-url "${STEELSEARCH_NODE_A_URL}" \
    --node-b-url "${STEELSEARCH_NODE_B_URL}" \
    --output "${MULTI_NODE_TRANSPORT_ADMIN_REPORT}"
fi
if [[ "${RUN_SEARCH_COMPAT}" == "1" ]]; then
  compat_args=(--report "${REPORT_PATH}" --wait --timeout "${SEARCH_COMPAT_TIMEOUT:-10}")
  if [[ -n "${SEARCH_COMPAT_FIXTURE:-}" ]]; then
    compat_args+=(--fixture "${SEARCH_COMPAT_FIXTURE}")
  fi

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
if [[ "${RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION:-0}" == "1" ]]; then
  echo "multi-node transport/admin integration report: ${MULTI_NODE_TRANSPORT_ADMIN_REPORT}"
fi
if [[ "${PHASE_A_COMPARE_SCOPE}" != "search" && "${PHASE_A_COMPARE_SCOPE}" != "snapshot-migration" && "${PHASE_A_COMPARE_SCOPE}" != "vector-ml" && "${PHASE_A_COMPARE_SCOPE}" != "transport-admin" ]]; then
  echo "migration validation report: ${VALIDATION_REPORT_PATH}"
fi
