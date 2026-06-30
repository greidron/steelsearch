#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
FIXTURE="$ROOT_DIR/tools/fixtures/java-mixed-cluster-binary-profiles.json"
PROFILE=""
REPORT_DIR="$ROOT_DIR/target/java-mixed-cluster-binary"
PREPARE_CMD=""
WRITE_CMD=""
READ_CMD=""
RECOVER_CMD=""
RESTART_CMD=""
CHECK_CMD=""

usage() {
  cat <<'EOF'
Usage:
  tools/run-java-mixed-cluster-binary-harness.sh --profile <name> [options]

Options:
  --fixture <path>        Profile fixture path
  --report-dir <dir>      Report root (default: target/java-mixed-cluster-binary)
  --prepare-cmd <cmd>     Cluster/data setup command
  --write-cmd <cmd>       Primary write command
  --read-cmd <cmd>        Readback verification command
  --recover-cmd <cmd>     Recovery trigger/verification command
  --restart-cmd <cmd>     Restart command
  --check-cmd <cmd>       Final compatibility assertion command
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --fixture) FIXTURE="$2"; shift 2 ;;
    --report-dir) REPORT_DIR="$2"; shift 2 ;;
    --prepare-cmd) PREPARE_CMD="$2"; shift 2 ;;
    --write-cmd) WRITE_CMD="$2"; shift 2 ;;
    --read-cmd) READ_CMD="$2"; shift 2 ;;
    --recover-cmd) RECOVER_CMD="$2"; shift 2 ;;
    --restart-cmd) RESTART_CMD="$2"; shift 2 ;;
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
PHASE_ARTIFACT_DIR="$REPORT_DIR/$PROFILE/phase-artifacts"
LOG_DIR="$REPORT_DIR/$PROFILE/logs"
mkdir -p "$PHASE_ARTIFACT_DIR" "$LOG_DIR"

run_phase() {
  local phase="$1"
  local cmd="$2"
  local log_path="$LOG_DIR/$phase.log"
  if [[ -z "$cmd" ]]; then
    echo "missing command for phase: $phase" >&2
    exit 1
  fi
  echo "[$phase] $cmd"
  if ! JAVA_MIXED_CLUSTER_REPORT_DIR="$REPORT_DIR/$PROFILE" \
    JAVA_MIXED_CLUSTER_PHASE_ARTIFACT_DIR="$PHASE_ARTIFACT_DIR" \
    JAVA_MIXED_CLUSTER_PHASE_ARTIFACT_PATH="$PHASE_ARTIFACT_DIR/$phase.json" \
    JAVA_MIXED_CLUSTER_PHASE_NAME="$phase" \
      bash -lc "$cmd" >"$log_path" 2>&1; then
    cat "$log_path"
    return 1
  fi
  cat "$log_path"
}

run_phase "prepare" "$PREPARE_CMD"
run_phase "write" "$WRITE_CMD"
run_phase "read" "$READ_CMD"
run_phase "recover" "$RECOVER_CMD"
run_phase "restart" "$RESTART_CMD"
run_phase "check" "$CHECK_CMD"

PROFILE_JSON="$profile_json" LOG_DIR="$LOG_DIR" python3 - "$PROFILE" "$REPORT_PATH" <<'PY'
import json
import os
import sys
from pathlib import Path

profile_name = sys.argv[1]
report_path = Path(sys.argv[2])
profile = json.loads(os.environ["PROFILE_JSON"])
phase_artifact_dir = report_path.parent / "phase-artifacts"
log_dir = Path(os.environ["LOG_DIR"])
logs = {
    phase: (log_dir / f"{phase}.log").read_text(encoding="utf-8", errors="replace")
    for phase in profile["required_phases"]
}
combined_logs = "\n".join(logs.values())
expected_markers = profile.get("expected_markers", [])
marker_hits = {marker: (marker in combined_logs) for marker in expected_markers}
missing_markers = [marker for marker, matched in marker_hits.items() if not matched]
phase_artifacts = {}
phase_payloads = {}
for phase in profile["required_phases"]:
    candidate = phase_artifact_dir / f"{phase}.json"
    if candidate.exists():
        phase_artifacts[phase] = str(candidate)
        phase_payloads[phase] = json.loads(candidate.read_text())

report = {
    "profile": profile_name,
    "primary_node": profile["primary_node"],
    "replica_node": profile["replica_node"],
    "required_phases": profile["required_phases"],
    "expected_markers": expected_markers,
    "marker_hits": marker_hits,
    "missing_markers": missing_markers,
    "write_modes": profile.get("write_modes", []),
    "visibility_stages": profile.get("visibility_stages", []),
    "checkpoint_fields": profile.get("checkpoint_fields", []),
    "checkpoint_drift": {
        field: 0 for field in profile.get("checkpoint_fields", [])
    },
    "replica_provenance_modes": profile.get("replica_provenance_modes", []),
    "replica_provenance": profile.get("replica_provenance"),
    "cluster_manager_visibility_modes": profile.get("cluster_manager_visibility_modes", []),
    "shard_routing_diff_fields": profile.get("shard_routing_diff_fields", []),
    "restart_durability_stages": profile.get("restart_durability_stages", []),
    "restart_decoder_path": profile.get("restart_decoder_path"),
    "interruption_points": profile.get("interruption_points", []),
    "recovery_outcome_modes": profile.get("recovery_outcome_modes", []),
    "recovery_outcome": profile.get("recovery_outcome"),
    "cleanup_failure_class": profile.get("cleanup_failure_class"),
    "segment_matrix": profile.get("segment_matrix", []),
    "segment_metadata_fields": profile.get("segment_metadata_fields", []),
    "recovery_bootstrap_modes": profile.get("recovery_bootstrap_modes", []),
    "recovery_bootstrap_mode": profile.get("recovery_bootstrap_mode"),
    "incompatibility_failure_class": profile.get("incompatibility_failure_class"),
    "required_failure_classes": profile.get("required_failure_classes", []),
    "phase_logs": {phase: str(log_dir / f"{phase}.log") for phase in logs},
    "phase_artifacts": phase_artifacts,
    "artifact_source": "actual-phase-artifacts" if phase_artifacts else "profile-defaults",
    "status": "failed" if missing_markers else "completed"
}

for payload in phase_payloads.values():
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "phase":
                continue
            report[key] = value

report_path.write_text(json.dumps(report, indent=2) + "\n")
if missing_markers:
    print(
        "java mixed-cluster binary harness missing expected marker(s): "
        + ", ".join(missing_markers),
        file=sys.stderr,
    )
    raise SystemExit(1)
PY

echo "java mixed cluster binary harness completed"
