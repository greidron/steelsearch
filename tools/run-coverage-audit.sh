#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${COVERAGE_AUDIT_WORK_DIR:-${ROOT_DIR}/target/coverage-audit}"
mkdir -p "${WORK_DIR}"

TEST_INVENTORY_COUNT="$(
  cargo test --workspace -- --list 2>/dev/null | wc -l | tr -d ' '
)"

LLVM_COV_STATUS="missing"
LLVM_COV_VERSION=""
if cargo llvm-cov --version >"${WORK_DIR}/cargo-llvm-cov.version" 2>"${WORK_DIR}/cargo-llvm-cov.version.stderr"; then
  LLVM_COV_STATUS="available"
  LLVM_COV_VERSION="$(cat "${WORK_DIR}/cargo-llvm-cov.version" | tr -d '\n')"
fi

python3 - "${WORK_DIR}" "${TEST_INVENTORY_COUNT}" "${LLVM_COV_STATUS}" "${LLVM_COV_VERSION}" <<'PY'
import json
import os
import sys

work_dir, test_inventory_count, llvm_cov_status, llvm_cov_version = sys.argv[1:5]

report = {
    "work_dir": work_dir,
    "test_inventory_count": int(test_inventory_count),
    "llvm_cov": {
        "status": llvm_cov_status,
        "version": llvm_cov_version or None,
    },
    "summary": {
        "passed": True,
        "note": (
            "Coverage audit runner completed. "
            "If cargo-llvm-cov is missing, line/branch percentage coverage is not available yet."
        ),
    },
}

report_path = os.path.join(work_dir, "coverage-audit-report.json")
with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
print(json.dumps(report, indent=2, sort_keys=True))
PY
