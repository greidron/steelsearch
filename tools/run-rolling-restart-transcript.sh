#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
FIXTURE="$ROOT_DIR/tools/fixtures/rolling-restart-transcript-profiles.json"
PROFILE=""
REPORT=""
PREPARE_CMD=""

declare -A STEP_CMDS=()

usage() {
  cat <<'EOF'
Usage:
  tools/run-rolling-restart-transcript.sh --profile <rolling-restart|rolling-upgrade> [options]

Options:
  --fixture <path>             Override transcript fixture path
  --report <path>              Report output path
  --prepare-cmd <cmd>          Command to run before the ordered step sequence
  --step-cmd <step=cmd>        Step command mapping; repeat for each fixture step
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --fixture) FIXTURE="$2"; shift 2 ;;
    --report) REPORT="$2"; shift 2 ;;
    --prepare-cmd) PREPARE_CMD="$2"; shift 2 ;;
    --step-cmd)
      step_name="${2%%=*}"
      step_cmd="${2#*=}"
      if [[ -z "$step_name" || "$step_name" == "$step_cmd" ]]; then
        echo "--step-cmd requires step=cmd format" >&2
        exit 1
      fi
      STEP_CMDS["$step_name"]="$step_cmd"
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ -z "$PROFILE" ]]; then
  echo "--profile is required" >&2
  exit 1
fi

if [[ ! -f "$FIXTURE" ]]; then
  echo "fixture not found: $FIXTURE" >&2
  exit 1
fi

if [[ -z "$REPORT" ]]; then
  REPORT="$ROOT_DIR/target/rolling-restart-transcript-${PROFILE}.json"
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

mapfile -t REQUIRED_STEPS < <(PROFILE_JSON="$profile_json" python3 - <<'PY'
import json
import os

profile = json.loads(os.environ["PROFILE_JSON"])
for step in profile.get("steps", []):
    print(step)
PY
)

for step in "${REQUIRED_STEPS[@]}"; do
  if [[ -z "${STEP_CMDS[$step]:-}" ]]; then
    echo "missing --step-cmd for required step: $step" >&2
    exit 1
  fi
done

run_cmd() {
  local label="$1"
  local cmd="$2"
  echo "[$label] $cmd"
  bash -lc "$cmd"
}

declare -a TRANSCRIPT_LINES=()

if [[ -n "$PREPARE_CMD" ]]; then
  run_cmd "prepare" "$PREPARE_CMD"
fi

for step in "${REQUIRED_STEPS[@]}"; do
  run_cmd "$step" "${STEP_CMDS[$step]}"
  TRANSCRIPT_LINES+=("$step")
done

mkdir -p "$(dirname "$REPORT")"
PROFILE_JSON="$profile_json" TRANSCRIPT_JSON="$(printf '%s\n' "${TRANSCRIPT_LINES[@]}" | python3 -c 'import json,sys; print(json.dumps([line.strip() for line in sys.stdin if line.strip()]))')" FIXTURE_PATH="$FIXTURE" python3 - "$PROFILE" "$REPORT" <<'PY'
import json
import os
import sys
from pathlib import Path

profile_name = sys.argv[1]
report_path = Path(sys.argv[2])
profile = json.loads(os.environ["PROFILE_JSON"])
transcript = json.loads(os.environ["TRANSCRIPT_JSON"])
report = {
    "profile": profile_name,
    "fixture": os.environ["FIXTURE_PATH"],
    "steps": profile.get("steps", []),
    "transcript_assertions": profile.get("transcript_assertions", []),
    "transcript": transcript,
    "status": "completed",
}
report_path.write_text(json.dumps(report, indent=2) + "\n")
PY

echo "rolling restart transcript completed"
