#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE_PATH="${ROOT_DIR}/tools/fixtures/mixed-cluster-recovery-wire.json"
WORK_DIR="${PHASE_C_RECOVERY_WORK_DIR:-${ROOT_DIR}/target/phase-c-mixed-cluster-recovery}"
REPORT_PATH="${WORK_DIR}/bounded-peer-recovery-probe-report.json"
mkdir -p "${WORK_DIR}"

python3 - "${FIXTURE_PATH}" "${WORK_DIR}" <<'PY'
import json
import os
import sys

fixture_path, work_dir = sys.argv[1:3]
with open(fixture_path, "r", encoding="utf-8") as fh:
    fixture = json.load(fh)["recovery_wire_fixture"]

artifact_map = {
    "start_request": "recovery-start-request.json",
    "chunk_request": "recovery-chunk-request.json",
    "translog_request": "recovery-translog-request.json",
    "finalize_request": "recovery-finalize-request.json",
    "response": "recovery-response.json",
}
for key, filename in artifact_map.items():
    path = os.path.join(work_dir, filename)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(fixture[key], fh, indent=2, sort_keys=True)
PY

TEST_STDOUT="${WORK_DIR}/recovery-wire.stdout"
TEST_STDERR="${WORK_DIR}/recovery-wire.stderr"
if cargo test -p os-transport mixed_cluster_recovery_wire_fixture_round_trips_all_claimed_shapes --lib -- --nocapture >"${TEST_STDOUT}" 2>"${TEST_STDERR}"; then
  python3 - "${FIXTURE_PATH}" "${WORK_DIR}" "${REPORT_PATH}" <<'PY'
import json
import os
import sys

fixture_path, work_dir, report_path = sys.argv[1:4]
report = {
    "fixture": fixture_path,
    "artifacts": {
        "start_request": os.path.join(work_dir, "recovery-start-request.json"),
        "chunk_request": os.path.join(work_dir, "recovery-chunk-request.json"),
        "translog_request": os.path.join(work_dir, "recovery-translog-request.json"),
        "finalize_request": os.path.join(work_dir, "recovery-finalize-request.json"),
        "response": os.path.join(work_dir, "recovery-response.json"),
    },
    "checks": {
        "wire_round_trip_passed": True
    },
    "summary": {
        "passed": True
    }
}
with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
print(json.dumps(report, indent=2, sort_keys=True))
PY
else
  cat "${TEST_STDOUT}" >&2 || true
  cat "${TEST_STDERR}" >&2 || true
  exit 1
fi
