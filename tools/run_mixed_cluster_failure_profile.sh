#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${PHASE_C_FAILURE_WORK_DIR:-${ROOT_DIR}/target/phase-c-mixed-cluster-failure}"
mkdir -p "${WORK_DIR}"

LIVE_REPORT="${WORK_DIR}/failure-topology-probe-report.json"
LEDGER_REPORT="${WORK_DIR}/failure-ledger-report.json"
FINAL_REPORT="${WORK_DIR}/mixed-cluster-failure-report.json"

bash "${ROOT_DIR}/tools/probe_mixed_cluster_failure_profile.sh" >"${LIVE_REPORT}"

LEDGER_STDOUT="${WORK_DIR}/failure-ledger.stdout"
LEDGER_STDERR="${WORK_DIR}/failure-ledger.stderr"
if cargo test -p os-core mixed_cluster_failure_ledger_covers_publication_mismatch_routing_hole_and_stale_replica --test mixed_cluster_failure_ledger -- --nocapture >"${LEDGER_STDOUT}" 2>"${LEDGER_STDERR}"; then
  python3 - "${LEDGER_REPORT}" <<'PY'
import json
import sys

report_path = sys.argv[1]
report = {"summary": {"passed": True}}
with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY
else
  cat "${LEDGER_STDOUT}" >&2 || true
  cat "${LEDGER_STDERR}" >&2 || true
  exit 1
fi

python3 - "${LIVE_REPORT}" "${LEDGER_REPORT}" "${FINAL_REPORT}" <<'PY'
import json
import sys

live_path, ledger_path, final_path = sys.argv[1:4]
with open(live_path, "r", encoding="utf-8") as fh:
    live = json.load(fh)
with open(ledger_path, "r", encoding="utf-8") as fh:
    ledger = json.load(fh)

report = {
    "reports": {
        "failure_topology_probe_report": live_path,
        "failure_ledger_report": ledger_path,
    },
    "checks": {
        "failure_topology_probe_passed": bool(live.get("summary", {}).get("passed")),
        "failure_ledger_passed": bool(ledger.get("summary", {}).get("passed")),
    },
}
report["summary"] = {
    "passed": all(report["checks"].values())
}

with open(final_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
print(json.dumps(report, indent=2, sort_keys=True))
PY
