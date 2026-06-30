#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
FIXTURE="$ROOT_DIR/tools/fixtures/phase-b-gap-harness-profiles.json"
PROFILE=""
REPORT_DIR="$ROOT_DIR/target/phase-b-gap"
PREPARE_CMD=""
TRIGGER_CMD=""
CHECK_CMD=""

usage() {
  cat <<'EOF'
Usage:
  tools/run-phase-b-gap-harness.sh --profile <name> [options]

Options:
  --fixture <path>       Profile fixture path
  --report-dir <dir>     Report root (default: target/phase-b-gap)
  --prepare-cmd <cmd>    Setup command before failure injection
  --trigger-cmd <cmd>    Trigger the failure condition
  --check-cmd <cmd>      Verify fail-closed outcome
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --fixture) FIXTURE="$2"; shift 2 ;;
    --report-dir) REPORT_DIR="$2"; shift 2 ;;
    --prepare-cmd) PREPARE_CMD="$2"; shift 2 ;;
    --trigger-cmd) TRIGGER_CMD="$2"; shift 2 ;;
    --check-cmd) CHECK_CMD="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ -z "$PROFILE" || -z "$PREPARE_CMD" || -z "$TRIGGER_CMD" || -z "$CHECK_CMD" ]]; then
  usage >&2
  exit 1
fi

if [[ ! -f "$FIXTURE" ]]; then
  echo "fixture not found: $FIXTURE" >&2
  exit 1
fi

mkdir -p "$REPORT_DIR/$PROFILE"
REPORT_PATH="$REPORT_DIR/$PROFILE/report.json"
LOG_DIR="$REPORT_DIR/$PROFILE/logs"
mkdir -p "$LOG_DIR"

profile_json=$(python3 - "$FIXTURE" "$PROFILE" <<'PY'
import json
import sys
from pathlib import Path

fixture = json.loads(Path(sys.argv[1]).read_text())
profile = fixture.get("profiles", {}).get(sys.argv[2])
if profile is None:
    print(f"unknown profile: {sys.argv[2]}", file=sys.stderr)
    raise SystemExit(1)
print(json.dumps(profile))
PY
)

run_phase() {
  local phase="$1"
  local cmd="$2"
  local log_path="$LOG_DIR/$phase.log"
  echo "[$phase] $cmd"
  if ! bash -lc "$cmd" >"$log_path" 2>&1; then
    cat "$log_path"
    return 1
  fi
  cat "$log_path"
}

run_phase "prepare" "$PREPARE_CMD"
run_phase "trigger" "$TRIGGER_CMD"
run_phase "check" "$CHECK_CMD"

PROFILE_JSON="$profile_json" LOG_DIR="$LOG_DIR" python3 - "$PROFILE" "$REPORT_PATH" <<'PY'
import json
import os
import sys
from pathlib import Path

profile = sys.argv[1]
report_path = Path(sys.argv[2])
profile_spec = json.loads(os.environ["PROFILE_JSON"])
log_dir = Path(os.environ["LOG_DIR"])
logs = {
    phase: (log_dir / f"{phase}.log").read_text(encoding="utf-8", errors="replace")
    for phase in ["prepare", "trigger", "check"]
}
combined_logs = "\n".join(logs.values())
expected_markers = profile_spec.get("expected_markers", [])
marker_hits = {marker: (marker in combined_logs) for marker in expected_markers}
missing_markers = [marker for marker, matched in marker_hits.items() if not matched]
report = {
    "profile": profile,
    "failure_class": profile_spec["failure_class"],
    "expected_markers": expected_markers,
    "marker_hits": marker_hits,
    "missing_markers": missing_markers,
    "phases": ["prepare", "trigger", "check"],
    "phase_logs": {phase: str(log_dir / f"{phase}.log") for phase in logs},
    "status": "failed" if missing_markers else "completed"
}
report_path.write_text(json.dumps(report, indent=2) + "\n")
if missing_markers:
    print(
        "phase-b gap harness missing expected marker(s): "
        + ", ".join(missing_markers),
        file=sys.stderr,
    )
    raise SystemExit(1)
PY

echo "phase-b gap harness completed"
