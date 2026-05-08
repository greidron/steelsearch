#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR=""
PROBE_REPORT=""
FAULT_CLASS=""
INDEX_NAME="mixed-java-negative-000001"
PRINT_ONLY=0
RECOVER_CMD=":"
RESTART_CMD=":"

usage() {
  cat <<'EOF'
Usage:
  tools/run_java_primary_rust_replica_negative_from_probe_report.sh --probe-report <path> --fault-class <name> [options]

Options:
  --probe-report <path>   Probe report containing success_harness_handoff
  --fault-class <name>    decode_mismatch | apply_mismatch | checkpoint_mismatch
  --report-dir <dir>      Report root
  --index <name>          Working index name
  --recover-cmd <cmd>     Recovery phase command override
  --restart-cmd <cmd>     Restart phase command override
  --print-only            Print the resolved negative recipe command instead of executing it
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --probe-report) PROBE_REPORT="$2"; shift 2 ;;
    --fault-class) FAULT_CLASS="$2"; shift 2 ;;
    --report-dir) REPORT_DIR="$2"; shift 2 ;;
    --index) INDEX_NAME="$2"; shift 2 ;;
    --recover-cmd) RECOVER_CMD="$2"; shift 2 ;;
    --restart-cmd) RESTART_CMD="$2"; shift 2 ;;
    --print-only) PRINT_ONLY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ -z "$PROBE_REPORT" || ! -f "$PROBE_REPORT" || -z "$FAULT_CLASS" ]]; then
  usage >&2
  exit 1
fi

if [[ -z "$REPORT_DIR" ]]; then
  REPORT_DIR="${ROOT_DIR}/target/java-primary-rust-negative-${FAULT_CLASS}"
fi

readarray -t HANDOFF < <(python3 - "$PROBE_REPORT" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
handoff = report.get("success_harness_handoff") or {}
print(handoff.get("cluster_url", ""))
print(handoff.get("java_node", ""))
print(handoff.get("rust_node", ""))
print("true" if report.get("membership_formed") else "false")
print(str(report.get("observed_node_count", 0)))
print(report.get("blocker_class", ""))
PY
)

CLUSTER_URL="${HANDOFF[0]:-}"
JAVA_NODE="${HANDOFF[1]:-}"
RUST_NODE="${HANDOFF[2]:-}"
MEMBERSHIP_FORMED="${HANDOFF[3]:-false}"
OBSERVED_NODE_COUNT="${HANDOFF[4]:-0}"
BLOCKER_CLASS="${HANDOFF[5]:-}"

if [[ -z "$CLUSTER_URL" || -z "$JAVA_NODE" || -z "$RUST_NODE" ]]; then
  echo "probe report missing success_harness_handoff fields" >&2
  exit 1
fi

if [[ "${MEMBERSHIP_FORMED}" != "true" || "${OBSERVED_NODE_COUNT}" -lt 2 ]]; then
  echo "probe report is not a true 2-node mixed cluster handoff: membership_formed=${MEMBERSHIP_FORMED} observed_node_count=${OBSERVED_NODE_COUNT} blocker_class=${BLOCKER_CLASS}" >&2
  exit 1
fi

python3 - "$CLUSTER_URL" <<'PY'
import json
import sys
import urllib.error
import urllib.request

base = sys.argv[1].rstrip("/")
request = urllib.request.Request(f"{base}/_cluster/health", method="GET")
try:
    with urllib.request.urlopen(request, timeout=5) as response:
        if response.status != 200:
            raise SystemExit(f"probe handoff endpoint returned unexpected status: {response.status}")
        json.loads(response.read().decode("utf-8", errors="replace") or "{}")
except Exception as exc:
    raise SystemExit(f"probe handoff endpoint is not live: {base} ({exc})")
PY

RECIPE="${ROOT_DIR}/tools/run_java_primary_rust_replica_negative_recipe.sh"
cmd=(
  bash
  "${RECIPE}"
  --cluster-url "${CLUSTER_URL}"
  --java-node "${JAVA_NODE}"
  --rust-node "${RUST_NODE}"
  --fault-class "${FAULT_CLASS}"
  --report-dir "${REPORT_DIR}"
  --index "${INDEX_NAME}"
  --recover-cmd "${RECOVER_CMD}"
  --restart-cmd "${RESTART_CMD}"
)

if [[ "$PRINT_ONLY" == "1" ]]; then
  printf '%q ' "${cmd[@]}"
  printf '\n'
  exit 0
fi

"${cmd[@]}"
