#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${PHASE_C_PUBLICATION_WORK_DIR:-${ROOT_DIR}/target/phase-c-mixed-cluster-publication}"
mkdir -p "${WORK_DIR}"

run_and_capture_test() {
  local report_path="$1"
  shift
  local test_cmd=("$@")
  local stdout_path="${report_path%.json}.stdout"
  local stderr_path="${report_path%.json}.stderr"
  if "${test_cmd[@]}" >"${stdout_path}" 2>"${stderr_path}"; then
    python3 - "$report_path" "${test_cmd[*]}" <<'PY'
import json
import sys

report_path, command = sys.argv[1:3]
report = {
    "command": command,
    "summary": {
        "passed": True
    }
}
with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY
  else
    cat "${stdout_path}" >&2 || true
    cat "${stderr_path}" >&2 || true
    return 1
  fi
}

run_and_capture_test \
  "${WORK_DIR}/publication-full-state-report.json" \
  cargo test -p os-cluster-state publication_full_state_receive_apply_replaces_local_cache --lib -- --nocapture

run_and_capture_test \
  "${WORK_DIR}/publication-diff-ack-report.json" \
  cargo test -p os-cluster-state publication_diff_apply_acknowledges_only_after_successful_apply --lib -- --nocapture

run_and_capture_test \
  "${WORK_DIR}/publication-reject-report.json" \
  cargo test -p os-cluster-state publication_reject_integration_preserves_cache_and_withholds_ack --lib -- --nocapture

python3 - "${WORK_DIR}" <<'PY'
import json
import os
import sys

work_dir = sys.argv[1]
report_files = [
    "publication-full-state-report.json",
    "publication-diff-ack-report.json",
    "publication-reject-report.json",
]

checks = {}
for name in report_files:
    path = os.path.join(work_dir, name)
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    checks[name] = bool(data.get("summary", {}).get("passed"))

report = {
    "reports": {name: os.path.join(work_dir, name) for name in report_files},
    "checks": checks,
    "summary": {
        "passed": all(checks.values())
    }
}
print(json.dumps(report, indent=2, sort_keys=True))
with open(os.path.join(work_dir, "mixed-cluster-publication-report.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY
