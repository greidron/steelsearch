#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REHEARSAL_DIR="${MULTINODE_REHEARSAL_DIR:-${ROOT}/target/multinode-rehearsal}"
CLUSTER_WORK_DIR="${STEELSEARCH_CLUSTER_WORK_DIR:-${REHEARSAL_DIR}/cluster}"
MANIFEST="${CLUSTER_WORK_DIR}/cluster.json"
LOG_DIR="${REHEARSAL_DIR}/logs"

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

python3 - "${MANIFEST}" <<'PY'
import json
import sys
import time
import urllib.request
from pathlib import Path

manifest_path = Path(sys.argv[1])
deadline = time.monotonic() + 120

while time.monotonic() < deadline:
    if not manifest_path.exists():
        time.sleep(0.25)
        continue
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    nodes = manifest.get("nodes", [])
    if nodes:
        ready = True
        for node in nodes:
            try:
                with urllib.request.urlopen(node["http_url"] + "/_steelsearch/dev/cluster", timeout=2.0) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                ready = ready and payload.get("formed") is True and payload.get("number_of_nodes") == len(nodes)
            except Exception:  # noqa: BLE001
                ready = False
                break
        if ready:
            print(json.dumps({"ready": True, "nodes": nodes}, indent=2))
            raise SystemExit(0)
    time.sleep(0.5)

raise SystemExit("multi-node Steelsearch cluster did not become ready")
PY

echo "Multi-node rehearsal passed"
