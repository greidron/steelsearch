#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${PHASE_C_PUBLICATION_WORK_DIR:-${ROOT_DIR}/target/phase-c-mixed-cluster-publication}"
mkdir -p "${WORK_DIR}"

run_and_capture_test() {
  local report_path="$1"
  local test_name="$2"
  local stage_csv="$3"
  shift 3
  local test_cmd=("$@")
  local stdout_path="${report_path%.json}.stdout"
  local stderr_path="${report_path%.json}.stderr"
  if "${test_cmd[@]}" >"${stdout_path}" 2>"${stderr_path}"; then
    python3 - "$report_path" "${test_name}" "${stage_csv}" "${test_cmd[*]}" <<'PY'
import json
import sys

report_path, test_name, stage_csv, command = sys.argv[1:5]
stages = [stage for stage in stage_csv.split(",") if stage]
report = {
    "command": command,
    "executed_tests": [test_name],
    "publication_stages": stages,
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
  "publication_full_state_receive_apply_replaces_local_cache" \
  "full_state_decode,local_cache_replace,apply_ack" \
  cargo test -p os-cluster-state publication_full_state_receive_apply_replaces_local_cache --lib -- --nocapture

run_and_capture_test \
  "${WORK_DIR}/publication-diff-ack-report.json" \
  "publication_diff_apply_acknowledges_only_after_successful_apply" \
  "diff_decode,diff_apply,apply_ack_after_success" \
  cargo test -p os-cluster-state publication_diff_apply_acknowledges_only_after_successful_apply --lib -- --nocapture

run_and_capture_test \
  "${WORK_DIR}/publication-reject-report.json" \
  "publication_reject_integration_preserves_cache_and_withholds_ack" \
  "reject_detected,cache_preserved,ack_withheld" \
  cargo test -p os-cluster-state publication_reject_integration_preserves_cache_and_withholds_ack --lib -- --nocapture

run_and_capture_test \
  "${WORK_DIR}/publication-repeated-diff-monotonicity-report.json" \
  "repeated_publication_diff_apply_requires_monotonic_versions_before_ack" \
  "repeated_diff_decode,monotonic_version_required,stale_round_rejected" \
  cargo test -p os-cluster-state repeated_publication_diff_apply_requires_monotonic_versions_before_ack --lib -- --nocapture

run_and_capture_test \
  "${WORK_DIR}/publication-reachable-catch-up-report.json" \
  "periodic_liveness_catches_up_reachable_lagging_publication_follower_before_retry" \
  "lagging_follower_detected,reachable_catch_up_applied,retry_suppressed" \
  cargo test -p os-node --features standalone-runtime periodic_liveness_catches_up_reachable_lagging_publication_follower_before_retry --bin steelsearch -- --nocapture

run_and_capture_test \
  "${WORK_DIR}/publication-scheduled-catch-up-report.json" \
  "periodic_liveness_schedules_node_left_publication_retry_before_fencing_manager" \
  "lagging_follower_detected,catch_up_scheduled_with_backoff,node_left_retry_after_backoff" \
  cargo test -p os-node --features standalone-runtime periodic_liveness_schedules_node_left_publication_retry_before_fencing_manager --bin steelsearch -- --nocapture

python3 - "${WORK_DIR}" <<'PY'
import json
import os
import sys

work_dir = sys.argv[1]
report_files = [
    "publication-full-state-report.json",
    "publication-diff-ack-report.json",
    "publication-reject-report.json",
    "publication-repeated-diff-monotonicity-report.json",
    "publication-reachable-catch-up-report.json",
    "publication-scheduled-catch-up-report.json",
]

checks = {}
executed_tests = []
publication_stages = []
child_executed_tests = {}
child_publication_stages = {}
for name in report_files:
    path = os.path.join(work_dir, name)
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    checks[name] = bool(data.get("summary", {}).get("passed"))
    tests = data.get("executed_tests") or []
    stages = data.get("publication_stages") or []
    if isinstance(tests, list):
        child_executed_tests[name] = tests
        executed_tests.extend(str(test) for test in tests)
    if isinstance(stages, list):
        child_publication_stages[name] = stages
        publication_stages.extend(str(stage) for stage in stages)

report = {
    "reports": {name: os.path.join(work_dir, name) for name in report_files},
    "checks": checks,
    "executed_tests": sorted(set(executed_tests)),
    "child_executed_tests": child_executed_tests,
    "publication_stages": sorted(set(publication_stages)),
    "child_publication_stages": child_publication_stages,
    "summary": {
        "passed": all(checks.values())
    }
}
print(json.dumps(report, indent=2, sort_keys=True))
with open(os.path.join(work_dir, "mixed-cluster-publication-report.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY
