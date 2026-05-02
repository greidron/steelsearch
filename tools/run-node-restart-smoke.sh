#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
FIXTURE="$ROOT_DIR/tools/fixtures/node-restart-smoke-profiles.json"
PROFILE=""
REPORT=""
PREPARE_CMD=""
STOP_CMD=""
START_CMD=""
CHECK_CMD=""
MUTATE_STATE_CMD=""
PID_FILE=""

usage() {
  cat <<'EOF'
Usage:
  tools/run-node-restart-smoke.sh --profile <clean-restart|dirty-restart|partial-state-restart> [options]

Options:
  --fixture <path>            Override profile fixture path
  --report <path>             Report output path
  --prepare-cmd <cmd>         Command to seed pre-restart writes
  --stop-cmd <cmd>            Command to stop the node
  --start-cmd <cmd>           Command to start the node
  --check-cmd <cmd>           Command to verify post-restart assertions
  --mutate-state-cmd <cmd>    Command to mutate partial persisted state
  --pid-file <path>           PID file used for dirty restart fallback kill -9
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --fixture) FIXTURE="$2"; shift 2 ;;
    --report) REPORT="$2"; shift 2 ;;
    --prepare-cmd) PREPARE_CMD="$2"; shift 2 ;;
    --stop-cmd) STOP_CMD="$2"; shift 2 ;;
    --start-cmd) START_CMD="$2"; shift 2 ;;
    --check-cmd) CHECK_CMD="$2"; shift 2 ;;
    --mutate-state-cmd) MUTATE_STATE_CMD="$2"; shift 2 ;;
    --pid-file) PID_FILE="$2"; shift 2 ;;
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
  REPORT="$ROOT_DIR/target/node-restart-smoke-${PROFILE}.json"
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

shutdown_mode=$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["shutdown_mode"])' <<<"$profile_json")
persisted_state_policy=$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["persisted_state_policy"])' <<<"$profile_json")

echo "profile=$PROFILE"
echo "shutdown_mode=$shutdown_mode"
echo "persisted_state_policy=$persisted_state_policy"
echo "report=$REPORT"

run_cmd() {
  local label="$1"
  local cmd="$2"
  if [[ -z "$cmd" ]]; then
    return 0
  fi
  echo "[$label] $cmd"
  bash -lc "$cmd"
}

dirty_stop() {
  if [[ -n "$STOP_CMD" ]]; then
    run_cmd "stop" "$STOP_CMD"
    return
  fi
  if [[ -z "$PID_FILE" || ! -f "$PID_FILE" ]]; then
    echo "dirty-restart requires --stop-cmd or a valid --pid-file" >&2
    exit 1
  fi
  local pid
  pid=$(cat "$PID_FILE")
  echo "[stop] kill -9 $pid"
  kill -9 "$pid"
}

if [[ -z "$START_CMD" || -z "$CHECK_CMD" ]]; then
  echo "--start-cmd and --check-cmd are required" >&2
  exit 1
fi

run_cmd "prepare" "$PREPARE_CMD"

case "$PROFILE" in
  clean-restart)
    if [[ -z "$STOP_CMD" ]]; then
      echo "clean-restart requires --stop-cmd" >&2
      exit 1
    fi
    run_cmd "stop" "$STOP_CMD"
    ;;
  dirty-restart)
    dirty_stop
    ;;
  partial-state-restart)
    if [[ -z "$STOP_CMD" || -z "$MUTATE_STATE_CMD" ]]; then
      echo "partial-state-restart requires --stop-cmd and --mutate-state-cmd" >&2
      exit 1
    fi
    run_cmd "stop" "$STOP_CMD"
    run_cmd "mutate-state" "$MUTATE_STATE_CMD"
    ;;
  *)
    echo "unsupported profile: $PROFILE" >&2
    exit 1
    ;;
esac

run_cmd "start" "$START_CMD"
run_cmd "check" "$CHECK_CMD"

mkdir -p "$(dirname "$REPORT")"
python3 - "$FIXTURE" "$PROFILE" "$REPORT" <<'PY'
import json
import sys
from pathlib import Path

fixture = json.loads(Path(sys.argv[1]).read_text())
profile_name = sys.argv[2]
report_path = Path(sys.argv[3])
profile = fixture["profiles"][profile_name]
report = {
    "profile": profile_name,
    "shutdown_mode": profile["shutdown_mode"],
    "persisted_state_policy": profile["persisted_state_policy"],
    "pre_restart_writes": profile.get("pre_restart_writes", []),
    "post_restart_reads": profile.get("post_restart_reads", []),
    "continuity_assertions": profile.get("continuity_assertions", []),
    "status": "completed"
}
if "state_mutation" in profile:
    report["state_mutation"] = profile["state_mutation"]
report_path.write_text(json.dumps(report, indent=2) + "\n")
PY

echo "node restart smoke completed"
