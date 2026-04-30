#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${PHASE_C_WORK_DIR:-${ROOT_DIR}/target/phase-c-mixed-cluster}"
mkdir -p "${WORK_DIR}"

PHASE_C_JOIN_WORK_DIR="${WORK_DIR}/join" \
  bash "${ROOT_DIR}/tools/run_mixed_cluster_join_profile.sh" >"${WORK_DIR}/mixed-cluster-join-report.json"

PHASE_C_PUBLICATION_WORK_DIR="${WORK_DIR}/publication" \
  bash "${ROOT_DIR}/tools/run_mixed_cluster_publication_profile.sh" >"${WORK_DIR}/mixed-cluster-publication-report.json"

PHASE_C_ALLOCATION_WORK_DIR="${WORK_DIR}/allocation" \
  bash "${ROOT_DIR}/tools/run_mixed_cluster_allocation_profile.sh" >"${WORK_DIR}/mixed-cluster-allocation-report.json"

PHASE_C_RECOVERY_WORK_DIR="${WORK_DIR}/recovery" \
  bash "${ROOT_DIR}/tools/run_mixed_cluster_recovery_profile.sh" >"${WORK_DIR}/mixed-cluster-recovery-report.json"

PHASE_C_WRITE_REPLICATION_WORK_DIR="${WORK_DIR}/write-replication" \
  bash "${ROOT_DIR}/tools/run_mixed_cluster_write_replication_profile.sh" >"${WORK_DIR}/mixed-cluster-write-replication-report.json"

PHASE_C_FAILURE_WORK_DIR="${WORK_DIR}/failure" \
  bash "${ROOT_DIR}/tools/run_mixed_cluster_failure_profile.sh" >"${WORK_DIR}/mixed-cluster-failure-report.json"

python3 - "${WORK_DIR}" <<'PY'
import json
import os
import sys

work_dir = sys.argv[1]
report_files = [
    "mixed-cluster-join-report.json",
    "mixed-cluster-publication-report.json",
    "mixed-cluster-allocation-report.json",
    "mixed-cluster-recovery-report.json",
    "mixed-cluster-write-replication-report.json",
    "mixed-cluster-failure-report.json",
]

reports = {}
passed = True
for name in report_files:
    path = os.path.join(work_dir, name)
    if not os.path.exists(path):
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

summary_path = os.path.join(work_dir, "phase-c-mixed-cluster-summary.json")
with open(summary_path, "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2, sort_keys=True)
print(json.dumps(summary, indent=2, sort_keys=True))
PY
