#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
FIXTURE="$ROOT_DIR/tools/fixtures/durability-compat-profiles.json"
PROFILE=""
STEELSEARCH_SNAPSHOT=""
OPENSEARCH_SNAPSHOT=""
REPORT_DIR="$ROOT_DIR/target/durability-compat"

usage() {
  cat <<'EOF'
Usage:
  tools/run-durability-compat.sh \
    --profile <standalone|secure-standalone> \
    --steelsearch-snapshot <dir> \
    --opensearch-snapshot <dir> \
    [--fixture <path>] \
    [--report-dir <dir>]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --steelsearch-snapshot) STEELSEARCH_SNAPSHOT="$2"; shift 2 ;;
    --opensearch-snapshot) OPENSEARCH_SNAPSHOT="$2"; shift 2 ;;
    --fixture) FIXTURE="$2"; shift 2 ;;
    --report-dir) REPORT_DIR="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ -z "$PROFILE" || -z "$STEELSEARCH_SNAPSHOT" || -z "$OPENSEARCH_SNAPSHOT" ]]; then
  usage >&2
  exit 1
fi

mkdir -p "$REPORT_DIR/$PROFILE"

python3 - "$FIXTURE" "$PROFILE" "$STEELSEARCH_SNAPSHOT" "$OPENSEARCH_SNAPSHOT" "$REPORT_DIR/$PROFILE/report.json" <<'PY'
import json
import sys
from pathlib import Path


def read_json(path: Path):
    return json.loads(path.read_text())


def get_field(doc, field):
    value = doc
    for part in field.split("."):
        value = value[part]
    return value


fixture = read_json(Path(sys.argv[1]))
profile = sys.argv[2]
steel_dir = Path(sys.argv[3])
open_dir = Path(sys.argv[4])
report_path = Path(sys.argv[5])

profile_spec = fixture.get("profiles", {}).get(profile)
if profile_spec is None:
    print(f"unknown profile: {profile}", file=sys.stderr)
    raise SystemExit(1)

results = []
passed = 0
failed = 0

for compare in profile_spec.get("compares", []):
    steel_file = steel_dir / compare["steelsearch_file"]
    open_file = open_dir / compare["opensearch_file"]
    result = {
        "name": compare["name"],
        "kind": compare["kind"],
        "steelsearch_file": str(steel_file),
        "opensearch_file": str(open_file)
    }
    if not steel_file.exists() or not open_file.exists():
        result["status"] = "failed"
        result["reason"] = "missing compare file"
        failed += 1
        results.append(result)
        continue

    steel_doc = read_json(steel_file)
    open_doc = read_json(open_file)

    if compare["kind"] == "json-equal":
        ok = steel_doc == open_doc
        result["status"] = "passed" if ok else "failed"
        if not ok:
          result["reason"] = "json mismatch"
    elif compare["kind"] == "numeric-field":
        steel_value = get_field(steel_doc, compare["field"])
        open_value = get_field(open_doc, compare["field"])
        result["steelsearch_value"] = steel_value
        result["opensearch_value"] = open_value
        ok = steel_value == open_value
        result["status"] = "passed" if ok else "failed"
        if not ok:
            result["reason"] = "numeric field mismatch"
    else:
        result["status"] = "failed"
        result["reason"] = f"unsupported compare kind: {compare['kind']}"
        ok = False

    if ok:
        passed += 1
    else:
        failed += 1
    results.append(result)

report = {
    "profile": profile,
    "steelsearch_snapshot": str(steel_dir),
    "opensearch_snapshot": str(open_dir),
    "summary": {
        "passed": passed,
        "failed": failed
    },
    "results": results
}
report_path.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report["summary"]))
raise SystemExit(0 if failed == 0 else 1)
PY
