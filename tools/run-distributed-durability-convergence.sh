#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
FIXTURE="$ROOT_DIR/tools/fixtures/distributed-durability-convergence-profiles.json"
PROFILE=""
REPORT=""
PREPARE_CMD=""
RELOCATE_CMD=""
RECOVER_CMD=""
DURABILITY_CMD=""
CHECK_CMD=""

usage() {
  cat <<'EOF'
Usage:
  tools/run-distributed-durability-convergence.sh --profile <name> [options]

Options:
  --fixture <path>         Override profile fixture path
  --report <path>          Report output path
  --prepare-cmd <cmd>      Prepare cluster/data before convergence probe
  --relocate-cmd <cmd>     Trigger relocation / node-left reroute
  --recover-cmd <cmd>      Trigger replica / peer recovery step
  --durability-cmd <cmd>   Trigger durability / retention verification step
  --check-cmd <cmd>        Final assertion command
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --fixture) FIXTURE="$2"; shift 2 ;;
    --report) REPORT="$2"; shift 2 ;;
    --prepare-cmd) PREPARE_CMD="$2"; shift 2 ;;
    --relocate-cmd) RELOCATE_CMD="$2"; shift 2 ;;
    --recover-cmd) RECOVER_CMD="$2"; shift 2 ;;
    --durability-cmd) DURABILITY_CMD="$2"; shift 2 ;;
    --check-cmd) CHECK_CMD="$2"; shift 2 ;;
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
  REPORT="$ROOT_DIR/target/distributed-durability-convergence/${PROFILE}/report.json"
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

run_phase() {
  local phase="$1"
  local cmd="$2"
  if [[ -z "$cmd" ]]; then
    echo "missing command for required phase: $phase" >&2
    exit 1
  fi
  echo "[$phase] $cmd"
  bash -lc "$cmd"
}

PHASE_LIST=$(PROFILE_JSON="$profile_json" python3 - <<'PY'
import json
import os
print("\n".join(json.loads(os.environ["PROFILE_JSON"]).get("phases", [])))
PY
)

while IFS= read -r phase; do
  [[ -z "$phase" ]] && continue
  case "$phase" in
    prepare) run_phase "$phase" "$PREPARE_CMD" ;;
    relocate) run_phase "$phase" "$RELOCATE_CMD" ;;
    recover) run_phase "$phase" "$RECOVER_CMD" ;;
    durability) run_phase "$phase" "$DURABILITY_CMD" ;;
    check) run_phase "$phase" "$CHECK_CMD" ;;
    *) echo "unsupported phase in fixture: $phase" >&2; exit 1 ;;
  esac
done <<<"$PHASE_LIST"

mkdir -p "$(dirname "$REPORT")"
PROFILE_JSON="$profile_json" python3 - "$PROFILE" "$REPORT" <<'PY'
import json
import os
import sys
from pathlib import Path

profile_name = sys.argv[1]
report_path = Path(sys.argv[2])
profile = json.loads(os.environ["PROFILE_JSON"])
report = {
    "profile": profile_name,
    "probe_case": profile["probe_case"],
    "shard_id": profile["shard_id"],
    "source_node": profile["source_node"],
    "target_node": profile["target_node"],
    "allocation_decision": profile["allocation_decision"],
    "relocation_phase": profile["relocation_phase"],
    "retention_lease_phase": profile["retention_lease_phase"],
    "timeline": profile["timeline"],
    "final_state": profile["final_state"],
    "direction": profile["direction"],
    "recovery_case": profile["recovery_case"],
    "file_chunk_phase": profile["file_chunk_phase"],
    "translog_phase": profile["translog_phase"],
    "finalize_phase": profile["finalize_phase"],
    "data_checksum_ok": profile["data_checksum_ok"],
    "doc_visibility_ok": profile["doc_visibility_ok"],
    "phases": profile.get("phases", []),
    "status": "completed"
}
report_path.write_text(json.dumps(report, indent=2) + "\n")
PY

echo "distributed durability convergence completed"
