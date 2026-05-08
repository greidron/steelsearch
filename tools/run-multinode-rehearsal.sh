#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REHEARSAL_DIR="${MULTINODE_REHEARSAL_DIR:-${ROOT}/target/multinode-rehearsal}"
CLUSTER_WORK_DIR="${STEELSEARCH_CLUSTER_WORK_DIR:-${REHEARSAL_DIR}/cluster}"
MANIFEST="${CLUSTER_WORK_DIR}/cluster.json"
LOG_DIR="${REHEARSAL_DIR}/logs"
STABILITY_WINDOW="${STEELSEARCH_STABILITY_WINDOW:-3}"
POLL_INTERVAL="${STEELSEARCH_STABILITY_POLL_INTERVAL:-0.5}"

usage() {
  cat <<'USAGE'
Run a local multi-node Steelsearch development rehearsal.

Environment:
  MULTINODE_REHEARSAL_DIR       Output/log directory. Default: target/multinode-rehearsal.
  STEELSEARCH_NODE_COUNT        Number of daemons. Default: 3.
  STEELSEARCH_HTTP_HOST         HTTP host. Default: 127.0.0.1.
  STEELSEARCH_BASE_HTTP_PORT    Optional first HTTP port.
  STEELSEARCH_BASE_TRANSPORT_PORT
                                 Optional first transport port.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

mkdir -p "${CLUSTER_WORK_DIR}" "${LOG_DIR}"
export STEELSEARCH_CLUSTER_WORK_DIR="${CLUSTER_WORK_DIR}"

"${ROOT}/tools/run-steelsearch-cluster-dev.sh" "$@" >"${LOG_DIR}/stdout.log" 2>"${LOG_DIR}/stderr.log" &
cluster_pid=$!

cleanup() {
  local status=$?
  if kill -0 "${cluster_pid}" 2>/dev/null; then
    kill "${cluster_pid}" 2>/dev/null || true
    wait "${cluster_pid}" 2>/dev/null || true
  fi
  if [[ "${status}" != "0" ]]; then
    echo "multi-node rehearsal logs: ${LOG_DIR}" >&2
    tail -120 "${LOG_DIR}/stderr.log" >&2 2>/dev/null || true
  fi
  exit "${status}"
}
trap cleanup EXIT INT TERM

python3 "${ROOT}/tools/check-multinode-rehearsal.py" \
  "${MANIFEST}" \
  --stability-window "${STABILITY_WINDOW}" \
  --poll-interval "${POLL_INTERVAL}"

echo "Multi-node rehearsal passed"
