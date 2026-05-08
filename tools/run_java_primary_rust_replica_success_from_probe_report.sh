#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="java-primary-rust-replica"
REPORT_DIR="${ROOT_DIR}/target/java-mixed-cluster-binary"
PROBE_REPORT=""
INDEX_NAME="mixed-java-success-000001"
PRINT_ONLY=0
RECOVER_CMD=""
RESTART_CMD=""

usage() {
  cat <<'EOF'
Usage:
  tools/run_java_primary_rust_replica_success_from_probe_report.sh --probe-report <path> [options]

Options:
  --probe-report <path>   Probe report containing success_harness_handoff
  --report-dir <dir>      Report root
  --index <name>          Working index name
  --recover-cmd <cmd>     Recovery phase command override
  --restart-cmd <cmd>     Restart phase command override
  --print-only            Print the resolved harness command instead of executing it
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --probe-report) PROBE_REPORT="$2"; shift 2 ;;
    --report-dir) REPORT_DIR="$2"; shift 2 ;;
    --index) INDEX_NAME="$2"; shift 2 ;;
    --recover-cmd) RECOVER_CMD="$2"; shift 2 ;;
    --restart-cmd) RESTART_CMD="$2"; shift 2 ;;
    --print-only) PRINT_ONLY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ -z "$PROBE_REPORT" || ! -f "$PROBE_REPORT" ]]; then
  echo "probe report not found: $PROBE_REPORT" >&2
  usage >&2
  exit 1
fi

readarray -t HANDOFF < <(python3 - "$PROBE_REPORT" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
handoff = report.get("success_harness_handoff") or {}
cluster_url = handoff.get("cluster_url", "")
java_node = handoff.get("java_node", "")
rust_node = handoff.get("rust_node", "")
print(cluster_url)
print(java_node)
print(rust_node)
PY
)

CLUSTER_URL="${HANDOFF[0]:-}"
JAVA_NODE="${HANDOFF[1]:-}"
RUST_NODE="${HANDOFF[2]:-}"

if [[ -z "$CLUSTER_URL" || -z "$JAVA_NODE" || -z "$RUST_NODE" ]]; then
  echo "probe report missing success_harness_handoff fields" >&2
  exit 1
fi

STATE_DIR="${REPORT_DIR}/${PROFILE}/runtime-state"
PYTHON_ENTRY="${ROOT_DIR}/tools/run_java_primary_rust_replica_actual.py"
HARNESS="${ROOT_DIR}/tools/run-java-mixed-cluster-binary-harness.sh"
COMMON_ARGS="--cluster-url ${CLUSTER_URL@Q} --index ${INDEX_NAME@Q} --java-node ${JAVA_NODE@Q} --rust-node ${RUST_NODE@Q} --state-dir ${STATE_DIR@Q}"

if [[ -z "$RECOVER_CMD" ]]; then
  RECOVER_CMD="python3 ${PYTHON_ENTRY@Q} ${COMMON_ARGS} --probe-report ${PROBE_REPORT@Q} recover"
fi

if [[ -z "$RESTART_CMD" ]]; then
  RESTART_CMD="python3 ${PYTHON_ENTRY@Q} ${COMMON_ARGS} restart"
fi

cmd=(
  "${HARNESS}"
  --profile "${PROFILE}"
  --report-dir "${REPORT_DIR}"
  --prepare-cmd "python3 ${PYTHON_ENTRY@Q} ${COMMON_ARGS} prepare"
  --write-cmd "python3 ${PYTHON_ENTRY@Q} ${COMMON_ARGS} write"
  --read-cmd "python3 ${PYTHON_ENTRY@Q} ${COMMON_ARGS} read"
  --recover-cmd "${RECOVER_CMD}"
  --restart-cmd "${RESTART_CMD}"
  --check-cmd "python3 ${PYTHON_ENTRY@Q} ${COMMON_ARGS} check || test \$? -eq 2"
)

if [[ "$PRINT_ONLY" == "1" ]]; then
  printf '%q ' "${cmd[@]}"
  printf '\n'
  exit 0
fi

"${cmd[@]}"
