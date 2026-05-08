#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
FIXTURE="$ROOT_DIR/tools/fixtures/java-plugin-compat-layer-profiles.json"
PROFILE=""
REPORT_DIR="$ROOT_DIR/target/java-plugin-compat-layer"
PREPARE_CMD=""
BOOTSTRAP_CMD=""
CONFIG_CMD=""
REST_BIND_CMD=""
TRANSPORT_BIND_CMD=""
CHECK_CMD=""

usage() {
  cat <<'EOF'
Usage:
  tools/run-java-plugin-compat-layer-harness.sh --profile <name> [options]

Options:
  --fixture <path>            Profile fixture path
  --report-dir <dir>          Report root (default: target/java-plugin-compat-layer)
  --prepare-cmd <cmd>         Setup command
  --bootstrap-cmd <cmd>       Plugin bootstrap/load command
  --config-cmd <cmd>          Plugin config mutation command
  --rest-bind-cmd <cmd>       Plugin REST binding command
  --transport-bind-cmd <cmd>  Plugin transport binding command
  --check-cmd <cmd>           Final compatibility assertion command
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --fixture) FIXTURE="$2"; shift 2 ;;
    --report-dir) REPORT_DIR="$2"; shift 2 ;;
    --prepare-cmd) PREPARE_CMD="$2"; shift 2 ;;
    --bootstrap-cmd) BOOTSTRAP_CMD="$2"; shift 2 ;;
    --config-cmd) CONFIG_CMD="$2"; shift 2 ;;
    --rest-bind-cmd) REST_BIND_CMD="$2"; shift 2 ;;
    --transport-bind-cmd) TRANSPORT_BIND_CMD="$2"; shift 2 ;;
    --check-cmd) CHECK_CMD="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ -z "$PROFILE" ]]; then
  usage >&2
  exit 1
fi

if [[ ! -f "$FIXTURE" ]]; then
  echo "fixture not found: $FIXTURE" >&2
  exit 1
fi

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

mkdir -p "$REPORT_DIR/$PROFILE"
REPORT_PATH="$REPORT_DIR/$PROFILE/report.json"

run_phase() {
  local phase="$1"
  local cmd="$2"
  if [[ -z "$cmd" ]]; then
    echo "missing command for phase: $phase" >&2
    exit 1
  fi
  echo "[$phase] $cmd"
  bash -lc "$cmd"
}

PHASE_LIST=$(PROFILE_JSON="$profile_json" python3 - <<'PY'
import json
import os
print("\n".join(json.loads(os.environ["PROFILE_JSON"]).get("required_phases", [])))
PY
)

while IFS= read -r phase; do
  [[ -z "$phase" ]] && continue
  case "$phase" in
    prepare) run_phase "$phase" "$PREPARE_CMD" ;;
    bootstrap) run_phase "$phase" "$BOOTSTRAP_CMD" ;;
    config) run_phase "$phase" "$CONFIG_CMD" ;;
    rest-bind) run_phase "$phase" "$REST_BIND_CMD" ;;
    transport-bind) run_phase "$phase" "$TRANSPORT_BIND_CMD" ;;
    check) run_phase "$phase" "$CHECK_CMD" ;;
    *) echo "unsupported phase: $phase" >&2; exit 1 ;;
  esac
done <<<"$PHASE_LIST"

PROFILE_JSON="$profile_json" python3 - "$PROFILE" "$REPORT_PATH" <<'PY'
import json
import os
import sys
from pathlib import Path

profile_name = sys.argv[1]
report_path = Path(sys.argv[2])
profile = json.loads(os.environ["PROFILE_JSON"])
report = {
    "profile": profile_name,
    "required_phases": profile["required_phases"],
    "expected_markers": profile.get("expected_markers", []),
    "status": "completed"
}
report_path.write_text(json.dumps(report, indent=2) + "\n")
PY

echo "java plugin compat layer harness completed"
