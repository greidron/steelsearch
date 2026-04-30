#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${PHASE_C_FAILURE_WORK_DIR:-${ROOT_DIR}/target/phase-c-mixed-cluster-failure}"
mkdir -p "${WORK_DIR}"

JOIN_REPORT="${WORK_DIR}/failure-join-precheck-report.json"
JAVA_NODE_LOSS_REPORT="${WORK_DIR}/java-node-loss-report.json"
STEEL_NODE_LOSS_PUBLICATION_REPORT="${WORK_DIR}/steelsearch-node-loss-publication-report.json"
STEEL_NODE_LOSS_RECOVERY_REPORT="${WORK_DIR}/steelsearch-node-loss-recovery-report.json"

bash "${ROOT_DIR}/tools/probe_mixed_cluster_join_profile.sh" >"${JOIN_REPORT}"

JAVA_STDOUT="${WORK_DIR}/java-node-loss.stdout"
JAVA_STDERR="${WORK_DIR}/java-node-loss.stderr"
if cargo test -p os-transport shard_search_request_to_unavailable_node_returns_io_error --lib -- --nocapture >"${JAVA_STDOUT}" 2>"${JAVA_STDERR}"; then
  python3 - "${JAVA_NODE_LOSS_REPORT}" <<'PY'
import json
import sys

report_path = sys.argv[1]
report = {"summary": {"passed": True}}
with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY
else
  cat "${JAVA_STDOUT}" >&2 || true
  cat "${JAVA_STDERR}" >&2 || true
  exit 1
fi

PUB_STDOUT="${WORK_DIR}/steelsearch-node-loss-publication.stdout"
PUB_STDERR="${WORK_DIR}/steelsearch-node-loss-publication.stderr"
if cargo test -p os-cluster-state publication_reject_integration_preserves_cache_and_withholds_ack --lib -- --nocapture >"${PUB_STDOUT}" 2>"${PUB_STDERR}"; then
  python3 - "${STEEL_NODE_LOSS_PUBLICATION_REPORT}" <<'PY'
import json
import sys

report_path = sys.argv[1]
report = {"summary": {"passed": True}}
with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY
else
  cat "${PUB_STDOUT}" >&2 || true
  cat "${PUB_STDERR}" >&2 || true
  exit 1
fi

REC_STDOUT="${WORK_DIR}/steelsearch-node-loss-recovery.stdout"
REC_STDERR="${WORK_DIR}/steelsearch-node-loss-recovery.stderr"
if cargo test -p os-cluster-state mixed_cluster_recovery_fail_closed_fixture_matches_validator_behavior --lib -- --nocapture >"${REC_STDOUT}" 2>"${REC_STDERR}"; then
  python3 - "${STEEL_NODE_LOSS_RECOVERY_REPORT}" <<'PY'
import json
import sys

report_path = sys.argv[1]
report = {"summary": {"passed": True}}
with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY
else
  cat "${REC_STDOUT}" >&2 || true
  cat "${REC_STDERR}" >&2 || true
  exit 1
fi

python3 - "${JOIN_REPORT}" "${JAVA_NODE_LOSS_REPORT}" "${STEEL_NODE_LOSS_PUBLICATION_REPORT}" "${STEEL_NODE_LOSS_RECOVERY_REPORT}" <<'PY'
import json
import sys

join_path, java_loss_path, steel_pub_path, steel_recovery_path = sys.argv[1:5]
with open(join_path, "r", encoding="utf-8") as fh:
    join = json.load(fh)
with open(java_loss_path, "r", encoding="utf-8") as fh:
    java_loss = json.load(fh)
with open(steel_pub_path, "r", encoding="utf-8") as fh:
    steel_pub = json.load(fh)
with open(steel_recovery_path, "r", encoding="utf-8") as fh:
    steel_recovery = json.load(fh)

report = {
    "reports": {
        "failure_join_precheck_report": join_path,
        "java_node_loss_report": java_loss_path,
        "steelsearch_node_loss_publication_report": steel_pub_path,
        "steelsearch_node_loss_recovery_report": steel_recovery_path,
    },
    "checks": {
        "failure_join_precheck_passed": bool(join.get("summary", {}).get("passed")),
        "java_node_loss_fail_closed_passed": bool(java_loss.get("summary", {}).get("passed")),
        "steelsearch_node_loss_publication_fencing_passed": bool(steel_pub.get("summary", {}).get("passed")),
        "steelsearch_node_loss_recovery_fencing_passed": bool(steel_recovery.get("summary", {}).get("passed")),
    },
}
report["summary"] = {
    "passed": all(report["checks"].values())
}
print(json.dumps(report, indent=2, sort_keys=True))
PY
