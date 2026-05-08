#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
FIXTURE="$ROOT_DIR/tools/fixtures/migration-acceptance-dataset.json"
PROFILE="standalone-small-fixture"
REPORT_DIR="$ROOT_DIR/target/migration-acceptance"
SOURCE_SETUP_CMD=""
IMPORT_CMD=""
VERIFY_CMD=""
ROLLBACK_CMD=""
DIVERGENCE_CHECK_CMD=""
FROM_PHASE=""
TO_PHASE=""
ROLLBACK_ONLY=false
EVIDENCE_DIR=""
APPROVAL_FILE=""
REQUIRE_APPROVAL=false

usage() {
  cat <<'EOF'
Usage:
  tools/run-migration-acceptance-harness.sh [options]

Options:
  --fixture <path>                 Dataset fixture path
  --profile <name>                 Profile name (default: standalone-small-fixture)
  --report-dir <dir>               Report root (default: target/migration-acceptance)
  --source-setup-cmd <cmd>         Prepare source dataset
  --import-cmd <cmd>               Import into Steelsearch target
  --verify-cmd <cmd>               Verify target after import
  --rollback-cmd <cmd>             Perform rollback rehearsal
  --divergence-check-cmd <cmd>     Check source/target divergence after rollback
  --from-phase <phase>             Start from phase: source-setup|import|verify|rollback|divergence-check
  --to-phase <phase>               Stop after phase: source-setup|import|verify|rollback|divergence-check
  --rollback-only                  Run rollback and divergence-check only
  --evidence-dir <dir>             Write operator evidence archive to this directory
  --approval-file <path>           Approval transcript/record file
  --require-approval               Fail closed when approval file is missing
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fixture) FIXTURE="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --report-dir) REPORT_DIR="$2"; shift 2 ;;
    --source-setup-cmd) SOURCE_SETUP_CMD="$2"; shift 2 ;;
    --import-cmd) IMPORT_CMD="$2"; shift 2 ;;
    --verify-cmd) VERIFY_CMD="$2"; shift 2 ;;
    --rollback-cmd) ROLLBACK_CMD="$2"; shift 2 ;;
    --divergence-check-cmd) DIVERGENCE_CHECK_CMD="$2"; shift 2 ;;
    --from-phase) FROM_PHASE="$2"; shift 2 ;;
    --to-phase) TO_PHASE="$2"; shift 2 ;;
    --rollback-only) ROLLBACK_ONLY=true; shift 1 ;;
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2 ;;
    --approval-file) APPROVAL_FILE="$2"; shift 2 ;;
    --require-approval) REQUIRE_APPROVAL=true; shift 1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ ! -f "$FIXTURE" ]]; then
  echo "fixture not found: $FIXTURE" >&2
  exit 1
fi

ALL_PHASES=("source-setup" "import" "verify" "rollback" "divergence-check")
if $ROLLBACK_ONLY; then
  SELECTED_PHASES=("rollback" "divergence-check")
else
  start_index=0
  end_index=$((${#ALL_PHASES[@]} - 1))
  if [[ -n "$FROM_PHASE" ]]; then
    for i in "${!ALL_PHASES[@]}"; do
      if [[ "${ALL_PHASES[$i]}" == "$FROM_PHASE" ]]; then
        start_index=$i
      fi
    done
  fi
  if [[ -n "$TO_PHASE" ]]; then
    for i in "${!ALL_PHASES[@]}"; do
      if [[ "${ALL_PHASES[$i]}" == "$TO_PHASE" ]]; then
        end_index=$i
      fi
    done
  fi
  if (( start_index > end_index )); then
    echo "invalid phase range: from=$FROM_PHASE to=$TO_PHASE" >&2
    exit 1
  fi
  SELECTED_PHASES=("${ALL_PHASES[@]:$start_index:$((end_index - start_index + 1))}")
fi

phase_cmd() {
  case "$1" in
    source-setup) printf '%s' "$SOURCE_SETUP_CMD" ;;
    import) printf '%s' "$IMPORT_CMD" ;;
    verify) printf '%s' "$VERIFY_CMD" ;;
    rollback) printf '%s' "$ROLLBACK_CMD" ;;
    divergence-check) printf '%s' "$DIVERGENCE_CHECK_CMD" ;;
    *) return 1 ;;
  esac
}

for phase in "${SELECTED_PHASES[@]}"; do
  if [[ -z "$(phase_cmd "$phase")" ]]; then
    echo "missing command for selected phase: $phase" >&2
    exit 1
  fi
done

if $REQUIRE_APPROVAL && [[ -z "$APPROVAL_FILE" || ! -f "$APPROVAL_FILE" ]]; then
  echo "approval file is required and must exist" >&2
  exit 1
fi

mkdir -p "$REPORT_DIR/$PROFILE"
REPORT_PATH="$REPORT_DIR/$PROFILE/report.json"

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

PROFILE_JSON="$profile_json" SELECTED_PHASES_JSON="$(printf '%s\n' "${SELECTED_PHASES[@]}" | python3 -c 'import json,sys; print(json.dumps([line.strip() for line in sys.stdin if line.strip()]))')" python3 - <<'PY'
import json
import os
import sys

profile_spec = json.loads(os.environ["PROFILE_JSON"])
selected_phases = json.loads(os.environ["SELECTED_PHASES_JSON"])
datasets = profile_spec.get("rollback_divergence_datasets", [])
if "divergence-check" in selected_phases and len(datasets) < 2:
    print(
        "rollback divergence check requires at least two rollback_divergence_datasets",
        file=sys.stderr,
    )
    raise SystemExit(1)
PY

run_phase() {
  local phase="$1"
  local cmd="$2"
  echo "[$phase] $cmd"
  bash -lc "$cmd"
}

for phase in "${SELECTED_PHASES[@]}"; do
  run_phase "$phase" "$(phase_cmd "$phase")"
done

PROFILE_JSON="$profile_json" SELECTED_PHASES_JSON="$(printf '%s\n' "${SELECTED_PHASES[@]}" | python3 -c 'import json,sys; print(json.dumps([line.strip() for line in sys.stdin if line.strip()]))')" ALL_PHASES_JSON="$(printf '%s\n' "${ALL_PHASES[@]}" | python3 -c 'import json,sys; print(json.dumps([line.strip() for line in sys.stdin if line.strip()]))')" APPROVAL_FILE_PATH="$APPROVAL_FILE" REQUIRE_APPROVAL_FLAG="$REQUIRE_APPROVAL" FIXTURE_PATH="$FIXTURE" python3 - "$PROFILE" "$REPORT_PATH" <<'PY'
import json
import os
import sys
from pathlib import Path

profile = sys.argv[1]
report_path = Path(sys.argv[2])
profile_spec = json.loads(os.environ["PROFILE_JSON"])
selected_phases = json.loads(os.environ["SELECTED_PHASES_JSON"])
all_phases = json.loads(os.environ["ALL_PHASES_JSON"])
report = {
    "profile": profile,
    "fixture": os.environ["FIXTURE_PATH"],
    "source_index": profile_spec["source_index"],
    "alias": profile_spec["alias"],
    "expected_doc_count": profile_spec["expected_doc_count"],
    "metadata_expectations": profile_spec.get("metadata_expectations", []),
    "divergence_expectations": profile_spec.get("divergence_expectations", []),
    "rollback_divergence_datasets": profile_spec.get("rollback_divergence_datasets", []),
    "executed_phases": selected_phases,
    "skipped_phases": [phase for phase in all_phases if phase not in selected_phases],
    "approval_gate": {
        "required": os.environ["REQUIRE_APPROVAL_FLAG"] == "true",
        "approval_file": os.environ["APPROVAL_FILE_PATH"] or None,
        "present": bool(os.environ["APPROVAL_FILE_PATH"]),
    },
    "status": "completed"
}
report_path.write_text(json.dumps(report, indent=2) + "\n")
PY

if [[ -n "$EVIDENCE_DIR" ]]; then
  mkdir -p "$EVIDENCE_DIR"
  cp "$REPORT_PATH" "$EVIDENCE_DIR/report.json"
  python3 - "$EVIDENCE_DIR/evidence-manifest.json" "$REPORT_PATH" "$FIXTURE" "$APPROVAL_FILE" "$REQUIRE_APPROVAL" <<'PY'
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
report_path = Path(sys.argv[2]).resolve()
fixture_path = Path(sys.argv[3]).resolve()
approval_file = sys.argv[4]
require_approval = sys.argv[5] == "true"
manifest = {
    "report_path": str(report_path),
    "fixture_path": str(fixture_path),
    "rollback_divergence_datasets": json.loads(report_path.read_text()).get("rollback_divergence_datasets", []),
    "approval_gate": {
        "required": require_approval,
        "approval_file": str(Path(approval_file).resolve()) if approval_file else None,
        "present": bool(approval_file),
    },
}
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
PY
fi

echo "migration acceptance harness completed"
