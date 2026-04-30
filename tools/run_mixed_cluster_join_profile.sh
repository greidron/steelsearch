#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${PHASE_C_JOIN_WORK_DIR:-${ROOT_DIR}/target/phase-c-mixed-cluster-join}"
mkdir -p "${WORK_DIR}"

LIVE_REPORT="${WORK_DIR}/live-join-probe-report.json"
REJECT_REPORT="${WORK_DIR}/join-reject-report.json"
FINAL_REPORT="${WORK_DIR}/mixed-cluster-join-report.json"

bash "${ROOT_DIR}/tools/probe_mixed_cluster_join_profile.sh" >"${LIVE_REPORT}"

JOIN_REJECT_STDOUT="${WORK_DIR}/join-reject.stdout"
JOIN_REJECT_STDERR="${WORK_DIR}/join-reject.stderr"
if cargo test -p os-transport mixed_cluster_join_reject_fixture_matches_validator_behavior --lib -- --nocapture >"${JOIN_REJECT_STDOUT}" 2>"${JOIN_REJECT_STDERR}"; then
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
  cat "${JOIN_REJECT_STDOUT}" >&2 || true
  cat "${JOIN_REJECT_STDERR}" >&2 || true
  exit 1
fi

python3 - "${LIVE_REPORT}" "${REJECT_REPORT}" "${FINAL_REPORT}" <<'PY'
import json
import sys

live_path, reject_path, final_path = sys.argv[1:4]
with open(live_path, "r", encoding="utf-8") as fh:
    live = json.load(fh)
with open(reject_path, "r", encoding="utf-8") as fh:
    reject = json.load(fh)

report = {
    "reports": {
        "live_join_probe_report": live_path,
        "join_reject_report": reject_path,
    },
    "checks": {
        "live_join_probe_passed": bool(live.get("summary", {}).get("passed")),
        "join_reject_passed": bool(reject.get("summary", {}).get("passed")),
    },
}
report["summary"] = {
    "passed": all(report["checks"].values())
}

with open(final_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
print(json.dumps(report, indent=2, sort_keys=True))
PY
