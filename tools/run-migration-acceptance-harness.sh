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
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ ! -f "$FIXTURE" ]]; then
  echo "fixture not found: $FIXTURE" >&2
  exit 1
fi

if [[ -z "$SOURCE_SETUP_CMD" || -z "$IMPORT_CMD" || -z "$VERIFY_CMD" || -z "$ROLLBACK_CMD" || -z "$DIVERGENCE_CHECK_CMD" ]]; then
  echo "all phase commands are required" >&2
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

run_phase() {
  local phase="$1"
  local cmd="$2"
  echo "[$phase] $cmd"
  bash -lc "$cmd"
}

run_phase "source-setup" "$SOURCE_SETUP_CMD"
run_phase "import" "$IMPORT_CMD"
run_phase "verify" "$VERIFY_CMD"
run_phase "rollback" "$ROLLBACK_CMD"
run_phase "divergence-check" "$DIVERGENCE_CHECK_CMD"

PROFILE_JSON="$profile_json" python3 - "$PROFILE" "$REPORT_PATH" <<'PY'
import json
import os
import sys
from pathlib import Path

profile = sys.argv[1]
report_path = Path(sys.argv[2])
profile_spec = json.loads(os.environ["PROFILE_JSON"])
report = {
    "profile": profile,
    "source_index": profile_spec["source_index"],
    "alias": profile_spec["alias"],
    "expected_doc_count": profile_spec["expected_doc_count"],
    "metadata_expectations": profile_spec.get("metadata_expectations", []),
    "divergence_expectations": profile_spec.get("divergence_expectations", []),
    "phases": [
        "source-setup",
        "import",
        "verify",
        "rollback",
        "divergence-check"
    ],
    "status": "completed"
}
report_path.write_text(json.dumps(report, indent=2) + "\n")
PY

echo "migration acceptance harness completed"
