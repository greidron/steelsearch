#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="java-primary-rust-replica"
REPORT_DIR="${ROOT_DIR}/target/java-primary-rust-negative-recipe"
CLUSTER_URL=""
JAVA_NODE=""
RUST_NODE=""
INDEX_NAME="mixed-java-negative-000001"
FAULT_CLASS=""
RECOVER_CMD=":"
RESTART_CMD=":"

usage() {
  cat <<'EOF'
Usage:
  tools/run_java_primary_rust_replica_negative_recipe.sh [options]

Options:
  --cluster-url <url>      Mixed cluster coordinator URL
  --java-node <name>       Expected Java primary node name
  --rust-node <name>       Expected Rust replica node name
  --fault-class <name>     decode_mismatch | apply_mismatch | checkpoint_mismatch
  --report-dir <dir>       Report root
  --index <name>           Working index name
  --recover-cmd <cmd>      Recovery phase command override
  --restart-cmd <cmd>      Restart phase command override
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cluster-url) CLUSTER_URL="$2"; shift 2 ;;
    --java-node) JAVA_NODE="$2"; shift 2 ;;
    --rust-node) RUST_NODE="$2"; shift 2 ;;
    --fault-class) FAULT_CLASS="$2"; shift 2 ;;
    --report-dir) REPORT_DIR="$2"; shift 2 ;;
    --index) INDEX_NAME="$2"; shift 2 ;;
    --recover-cmd) RECOVER_CMD="$2"; shift 2 ;;
    --restart-cmd) RESTART_CMD="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ -z "$CLUSTER_URL" || -z "$JAVA_NODE" || -z "$RUST_NODE" || -z "$FAULT_CLASS" ]]; then
  usage >&2
  exit 1
fi

STATE_DIR="${REPORT_DIR}/${PROFILE}/runtime-state"
COMMON_ARGS="--cluster-url ${CLUSTER_URL@Q} --index ${INDEX_NAME@Q} --java-node ${JAVA_NODE@Q} --rust-node ${RUST_NODE@Q} --state-dir ${STATE_DIR@Q} --fault-class ${FAULT_CLASS@Q}"
PYTHON_ENTRY="${ROOT_DIR}/tools/run_java_primary_rust_replica_actual.py"
HARNESS="${ROOT_DIR}/tools/run-java-mixed-cluster-binary-harness.sh"

"${HARNESS}" \
  --profile "${PROFILE}" \
  --report-dir "${REPORT_DIR}" \
  --prepare-cmd "python3 ${PYTHON_ENTRY@Q} ${COMMON_ARGS} prepare" \
  --write-cmd "python3 ${PYTHON_ENTRY@Q} ${COMMON_ARGS} write" \
  --read-cmd "python3 ${PYTHON_ENTRY@Q} ${COMMON_ARGS} read" \
  --recover-cmd "${RECOVER_CMD}" \
  --restart-cmd "${RESTART_CMD}" \
  --check-cmd "python3 ${PYTHON_ENTRY@Q} ${COMMON_ARGS} check || test \$? -eq 2"
