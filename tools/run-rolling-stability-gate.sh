#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
FIXTURE="$ROOT_DIR/tools/fixtures/rolling-restart-transcript-profiles.json"
PROFILE=""
MANIFEST=""
REPORT=""
PREPARE_CMD=""
STABILITY_WINDOW="${STEELSEARCH_STABILITY_WINDOW:-3}"
POLL_INTERVAL="${STEELSEARCH_STABILITY_POLL_INTERVAL:-0.5}"
declare -A STEP_CMDS=()

usage() {
  cat <<'EOF'
Usage:
  tools/run-rolling-stability-gate.sh --profile <name> --manifest <cluster.json> [options]

Options:
  --fixture <path>          Profile fixture path
  --manifest <path>         Multi-node cluster manifest for readiness checks
  --report <path>           Report output path
  --prepare-cmd <cmd>       Optional setup command before rolling sequence
  --step-cmd step=cmd       Command mapped to a fixture step. Repeat as needed.
  --stability-window <sec>  Stability window passed to check-multinode-rehearsal.py
  --poll-interval <sec>     Poll interval passed to check-multinode-rehearsal.py
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --fixture) FIXTURE="$2"; shift 2 ;;
    --manifest) MANIFEST="$2"; shift 2 ;;
    --report) REPORT="$2"; shift 2 ;;
    --prepare-cmd) PREPARE_CMD="$2"; shift 2 ;;
    --step-cmd)
      key="${2%%=*}"
      value="${2#*=}"
      if [[ -z "$key" || "$key" == "$value" ]]; then
        echo "invalid --step-cmd mapping: $2" >&2
        exit 1
      fi
      STEP_CMDS["$key"]="$value"
      shift 2
      ;;
    --stability-window) STABILITY_WINDOW="$2"; shift 2 ;;
    --poll-interval) POLL_INTERVAL="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ -z "$PROFILE" || -z "$MANIFEST" ]]; then
  usage >&2
  exit 1
fi

if [[ ! -f "$FIXTURE" ]]; then
  echo "fixture not found: $FIXTURE" >&2
  exit 1
fi

if [[ ! -f "$MANIFEST" ]]; then
  echo "manifest not found: $MANIFEST" >&2
  exit 1
fi

if [[ -z "$REPORT" ]]; then
  REPORT="$ROOT_DIR/target/rolling-stability/${PROFILE}/report.json"
fi
DURABILITY_REPORT="$(dirname "$REPORT")/secure-durability-restart-report.json"

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

run_cmd() {
  local label="$1"
  local cmd="$2"
  echo "[$label] $cmd"
  bash -lc "$cmd"
}

if [[ -n "$PREPARE_CMD" ]]; then
  run_cmd "prepare" "$PREPARE_CMD"
fi

mkdir -p "$(dirname "$REPORT")"
tmp_transcript=$(mktemp)
trap 'rm -f "$tmp_transcript"' EXIT

PHASE_LIST=$(PROFILE_JSON="$profile_json" python3 - <<'PY'
import json
import os
print("\n".join(json.loads(os.environ["PROFILE_JSON"]).get("steps", [])))
PY
)

while IFS= read -r step; do
  [[ -z "$step" ]] && continue
  cmd="${STEP_CMDS[$step]:-}"
  if [[ -z "$cmd" ]]; then
    echo "missing --step-cmd for fixture step: $step" >&2
    exit 1
  fi
  run_cmd "$step" "$cmd"
  stability_json=$(python3 "$ROOT_DIR/tools/check-multinode-rehearsal.py" \
    "$MANIFEST" \
    --stability-window "$STABILITY_WINDOW" \
    --poll-interval "$POLL_INTERVAL")
  STABILITY_JSON="$stability_json" python3 - "$tmp_transcript" "$step" <<'PY'
import json
import os
import sys
from pathlib import Path

transcript_path = Path(sys.argv[1])
step = sys.argv[2]
entry = {
    "step": step,
    "stability": json.loads(os.environ["STABILITY_JSON"]),
}
existing = []
if transcript_path.exists() and transcript_path.read_text().strip():
    existing = json.loads(transcript_path.read_text())
existing.append(entry)
transcript_path.write_text(json.dumps(existing))
PY
done <<<"$PHASE_LIST"

PROFILE_JSON="$profile_json" python3 - "$PROFILE" "$REPORT" "$tmp_transcript" "$MANIFEST" "$STABILITY_WINDOW" "$POLL_INTERVAL" <<'PY'
import json
import os
import sys
from pathlib import Path

profile_name = sys.argv[1]
report_path = Path(sys.argv[2])
transcript_path = Path(sys.argv[3])
manifest = sys.argv[4]
stability_window = float(sys.argv[5])
poll_interval = float(sys.argv[6])
profile = json.loads(os.environ["PROFILE_JSON"])
transcript = json.loads(transcript_path.read_text()) if transcript_path.exists() else []
report = {
    "profile": profile_name,
    "manifest": manifest,
    "stability_window": stability_window,
    "poll_interval": poll_interval,
    "steps": profile["steps"],
    "transcript_assertions": profile.get("transcript_assertions", []),
    "stability_transcript": transcript,
    "status": "completed",
}
report_path.write_text(json.dumps(report, indent=2) + "\n")
PY

python3 "$ROOT_DIR/tools/emit-secure-durability-restart-report.py" \
  "$REPORT" \
  "$DURABILITY_REPORT"

echo "rolling stability gate completed"
