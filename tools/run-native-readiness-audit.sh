#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${NATIVE_READINESS_AUDIT_DIR:-${ROOT}/target/native-readiness-audit}"
COMPARE_DIR="${COMPARE_DIR:-${ROOT}/target/opensearch-compare}"
LIB_LOG="${NATIVE_READINESS_LIB_LOG:-${ROOT}/target/os-engine-tantivy-lib-test-after-grouped-wrapper-text-range-fixes.log}"
SEARCH_REPORT="${NATIVE_READINESS_SEARCH_REPORT:-${ROOT}/target/search-compat-report.json}"
FIXTURE_REPORT="${NATIVE_READINESS_FIXTURE_REPORT:-${OUT_DIR}/native-route-fixture-coverage-report.json}"
NATIVE_ROUTE_REPORT="${NATIVE_READINESS_ROUTE_REPORT:-${COMPARE_DIR}/native-route-coverage-report.json}"
READINESS_REPORT="${NATIVE_READINESS_REPORT:-${OUT_DIR}/native-readiness-artifacts-check.json}"
FIXTURE="${NATIVE_READINESS_FIXTURE:-${ROOT}/tools/fixtures/search-native-route-coverage.json}"

usage() {
  cat <<'USAGE'
Check the native-readiness artifact bundle.

This wrapper does not run the long lib-suite or OpenSearch comparison itself.
It validates the current artifacts and fails closed when any required readiness
gate is missing or red.

Environment:
  NATIVE_READINESS_AUDIT_DIR       Output directory. Default: target/native-readiness-audit.
  NATIVE_READINESS_LIB_LOG         Lib-suite log to inspect.
  NATIVE_READINESS_SEARCH_REPORT   Search compatibility report to inspect.
  NATIVE_READINESS_FIXTURE         Native-route fixture to preflight.
  NATIVE_READINESS_FIXTURE_REPORT  Fixture preflight report output.
  NATIVE_READINESS_ROUTE_REPORT    Native-route coverage report to inspect.
  NATIVE_READINESS_REPORT          Combined readiness report output.
  COMPARE_DIR                      Comparison output directory used when
                                   NATIVE_READINESS_ROUTE_REPORT is unset.
                                   Default: target/opensearch-compare.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

mkdir -p "${OUT_DIR}"

python3 "${ROOT}/tools/check-native-route-coverage-plan.py" \
  --output "${OUT_DIR}/native-route-coverage-plan-check.json"

python3 "${ROOT}/tools/check-native-route-fixture-coverage.py" \
  --fixture "${FIXTURE}" \
  --output "${FIXTURE_REPORT}"

python3 "${ROOT}/tools/check-native-readiness-artifacts.py" \
  --lib-log "${LIB_LOG}" \
  --search-compat-report "${SEARCH_REPORT}" \
  --native-route-fixture-report "${FIXTURE_REPORT}" \
  --native-route-report "${NATIVE_ROUTE_REPORT}" \
  --output "${READINESS_REPORT}"

echo "native readiness audit report: ${READINESS_REPORT}"
