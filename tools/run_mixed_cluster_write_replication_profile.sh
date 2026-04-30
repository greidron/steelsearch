#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${PHASE_C_WRITE_REPLICATION_WORK_DIR:-${ROOT_DIR}/target/phase-c-mixed-cluster-write-replication}"
mkdir -p "${WORK_DIR}"

HAPPY_REPORT="${WORK_DIR}/write-replication-happy-path-report.json"
REJECT_REPORT="${WORK_DIR}/write-replication-reject-report.json"
FINAL_REPORT="${WORK_DIR}/mixed-cluster-write-replication-report.json"

HAPPY_STDOUT="${WORK_DIR}/write-replication-happy-path.stdout"
HAPPY_STDERR="${WORK_DIR}/write-replication-happy-path.stderr"
if cargo test -p os-transport replica_operation_tcp_round_trip_preserves_replication_progress_metadata --lib -- --nocapture >"${HAPPY_STDOUT}" 2>"${HAPPY_STDERR}"; then
  python3 - "${HAPPY_REPORT}" <<'PY'
import json
import sys

report_path = sys.argv[1]
report = {
    "summary": {
        "passed": True
    }
}
with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY
else
  cat "${HAPPY_STDOUT}" >&2 || true
  cat "${HAPPY_STDERR}" >&2 || true
  exit 1
fi

REJECT_STDOUT="${WORK_DIR}/write-replication-reject.stdout"
REJECT_STDERR="${WORK_DIR}/write-replication-reject.stderr"
if cargo test -p os-transport mixed_cluster_write_replication_fail_closed_fixture_matches_validation_behavior --lib -- --nocapture >"${REJECT_STDOUT}" 2>"${REJECT_STDERR}"; then
  python3 - "${REJECT_REPORT}" <<'PY'
import json
import sys

report_path = sys.argv[1]
report = {
    "summary": {
        "passed": True
    }
}
with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY
else
  cat "${REJECT_STDOUT}" >&2 || true
  cat "${REJECT_STDERR}" >&2 || true
  exit 1
fi

python3 - "${HAPPY_REPORT}" "${REJECT_REPORT}" "${FINAL_REPORT}" <<'PY'
import json
import sys

happy_path, reject_path, final_path = sys.argv[1:4]
with open(happy_path, "r", encoding="utf-8") as fh:
    happy = json.load(fh)
with open(reject_path, "r", encoding="utf-8") as fh:
    reject = json.load(fh)

report = {
    "reports": {
        "write_replication_happy_path_report": happy_path,
        "write_replication_reject_report": reject_path,
    },
    "checks": {
        "write_replication_happy_path_passed": bool(happy.get("summary", {}).get("passed")),
        "write_replication_reject_passed": bool(reject.get("summary", {}).get("passed")),
    },
}
report["summary"] = {
    "passed": all(report["checks"].values())
}

with open(final_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
print(json.dumps(report, indent=2, sort_keys=True))
PY
