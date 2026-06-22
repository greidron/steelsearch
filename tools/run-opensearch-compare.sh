#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPARE_DIR="${COMPARE_DIR:-${ROOT}/target/opensearch-compare}"
REPORT_PATH="${SEARCH_COMPAT_REPORT:-${COMPARE_DIR}/search-compat-report.json}"
LOAD_COMPARISON_REPORT="${STEELSEARCH_LOAD_COMPARISON_REPORT:-${COMPARE_DIR}/http-load-comparison.json}"
NATIVE_ROUTE_COVERAGE_REPORT="${NATIVE_ROUTE_COVERAGE_REPORT:-${COMPARE_DIR}/native-route-coverage-report.json}"
NATIVE_ROUTE_FIXTURE_COVERAGE_REPORT="${NATIVE_ROUTE_FIXTURE_COVERAGE_REPORT:-${COMPARE_DIR}/native-route-fixture-coverage-report.json}"
UNIFIED_E2E_REPORT_DIR="${UNIFIED_E2E_REPORT_DIR:-${COMPARE_DIR}/unified-e2e}"
UNIFIED_E2E_MAX_REPORT_AGE_SECONDS="${UNIFIED_E2E_MAX_REPORT_AGE_SECONDS:-86400}"
REST_API_COVERAGE_REPORT="${REST_API_COVERAGE_REPORT:-${COMPARE_DIR}/rest-api-coverage-report.json}"
REST_API_MIN_LIVE_REQUIRED_MATCHED_SOURCE_ROUTE_COUNT="${REST_API_MIN_LIVE_REQUIRED_MATCHED_SOURCE_ROUTE_COUNT:-15}"

usage() {
  cat <<'USAGE'
Run Steelsearch/OpenSearch compatibility comparison tests.

This script reuses tools/run-development-replacement-rehearsal.sh for daemon
startup, search fixture comparison, migration validation, and readiness capture.
HTTP load comparison is opt-in because it is slower.

Environment:
  STEELSEARCH_URL                  Reuse an existing Steelsearch endpoint.
  OPENSEARCH_URL                   Reuse an existing OpenSearch endpoint.
  RUN_OPENSEARCH_COMPARISON=1      Required to run this long comparison.
  COMPARE_DIR                      Output/log directory. Default: target/opensearch-compare.
  SEARCH_COMPAT_REPORT             Search compatibility report path.
  RUN_HTTP_LOAD_COMPARISON=1       Also run tools/run-http-load-comparison.py.
  STEELSEARCH_LOAD_COMPARISON_REPORT
                                    Load comparison report path.
  RUN_NATIVE_ROUTE_COVERAGE=1      Also generate the Steelsearch native-route
                                    coverage report. This fails closed unless
                                    native observations satisfy the coverage plan.
  STEELSEARCH_NATIVE_ROUTE_OBSERVATIONS
                                    Optional JSON observations consumed by
                                    tools/generate-native-route-coverage-report.py.
  NATIVE_ROUTE_COVERAGE_REPORT     Native route coverage report path.
  NATIVE_ROUTE_FIXTURE_COVERAGE_REPORT
                                    Native route fixture preflight report path.
  RUN_ALIAS_TEMPLATE_PERSISTENCE_COMPARISON=1
                                    Include the alias/template persistence
                                    live parity report.
  RUN_UNIFIED_E2E_REPORT=1          Generate a unified E2E coverage/parity
                                    report from comparison outputs.
  UNIFIED_E2E_REPORT_DIR            Unified report directory. Default:
                                    COMPARE_DIR/unified-e2e.
  UNIFIED_E2E_MAX_REPORT_AGE_SECONDS
                                    Ignore unified suite reports older than
                                    this many seconds. Default: 86400.
  RUN_REST_API_SOURCE_COVERAGE=1     Generate source-inventory REST coverage
                                    from the unified E2E report and fail if
                                    live-required route coverage regresses.
  REST_API_COVERAGE_REPORT           REST API source coverage report path.
                                    Default: COMPARE_DIR/rest-api-coverage-report.json.
  REST_API_MIN_LIVE_REQUIRED_MATCHED_SOURCE_ROUTE_COUNT
                                    Minimum source route rows matched by
                                    live-required unified suites. Default: 15.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "${RUN_OPENSEARCH_COMPARISON:-0}" != "1" ]]; then
  echo "OpenSearch comparison is long-running; set RUN_OPENSEARCH_COMPARISON=1 to run it" >&2
  exit 2
fi

mkdir -p "${COMPARE_DIR}"
export REHEARSAL_DIR="${REHEARSAL_DIR:-${COMPARE_DIR}/rehearsal}"
export SEARCH_COMPAT_REPORT="${REPORT_PATH}"
export REQUIRE_OPENSEARCH_COMPARISON=1

if [[ "${RUN_NATIVE_ROUTE_COVERAGE:-0}" == "1" ]]; then
  native_route_fixture="${SEARCH_COMPAT_FIXTURE:-${ROOT}/tools/fixtures/search-strict-compat.json}"
  python3 "${ROOT}/tools/check-native-route-fixture-coverage.py" \
    --fixture "${native_route_fixture}" \
    --output "${NATIVE_ROUTE_FIXTURE_COVERAGE_REPORT}"
fi

"${ROOT}/tools/run-development-replacement-rehearsal.sh" "$@"

if [[ "${RUN_HTTP_LOAD_COMPARISON:-0}" == "1" ]]; then
  if [[ -z "${STEELSEARCH_URL:-}" || -z "${OPENSEARCH_URL:-}" ]]; then
    echo "RUN_HTTP_LOAD_COMPARISON=1 requires STEELSEARCH_URL and OPENSEARCH_URL to point at running endpoints" >&2
    exit 2
  fi
  python3 "${ROOT}/tools/run-http-load-comparison.py" \
    --steelsearch-url "${STEELSEARCH_URL%/}" \
    --opensearch-url "${OPENSEARCH_URL%/}" \
    --output "${LOAD_COMPARISON_REPORT}"
fi

if [[ "${RUN_ALIAS_TEMPLATE_PERSISTENCE_COMPARISON:-0}" == "1" ]]; then
  if [[ -z "${STEELSEARCH_URL:-}" || -z "${OPENSEARCH_URL:-}" ]]; then
    echo "RUN_ALIAS_TEMPLATE_PERSISTENCE_COMPARISON=1 requires STEELSEARCH_URL and OPENSEARCH_URL to point at running endpoints" >&2
    exit 2
  fi
  python3 "${ROOT}/tools/alias_template_persistence_compat.py" \
    --steelsearch-url "${STEELSEARCH_URL%/}" \
    --opensearch-url "${OPENSEARCH_URL%/}" \
    --output "${COMPARE_DIR}/alias-template-persistence-report.json"
fi

if [[ "${RUN_NATIVE_ROUTE_COVERAGE:-0}" == "1" ]]; then
  if [[ -z "${STEELSEARCH_NATIVE_ROUTE_OBSERVATIONS:-}" ]]; then
    STEELSEARCH_NATIVE_ROUTE_OBSERVATIONS="${COMPARE_DIR}/native-route-observations.json"
    python3 "${ROOT}/tools/extract-native-route-observations.py" \
      --search-compat-report "${REPORT_PATH}" \
      --output "${STEELSEARCH_NATIVE_ROUTE_OBSERVATIONS}"
  fi
  native_route_args=(
    --search-compat-report "${REPORT_PATH}"
    --output "${NATIVE_ROUTE_COVERAGE_REPORT}"
  )
  native_route_args+=(--native-observations "${STEELSEARCH_NATIVE_ROUTE_OBSERVATIONS}")
  python3 "${ROOT}/tools/generate-native-route-coverage-report.py" "${native_route_args[@]}"
fi

if [[ "${RUN_UNIFIED_E2E_REPORT:-0}" == "1" ]]; then
  python3 "${ROOT}/tools/run-unified-opensearch-e2e.py" \
    --output-dir "${UNIFIED_E2E_REPORT_DIR}" \
    --max-report-age-seconds "${UNIFIED_E2E_MAX_REPORT_AGE_SECONDS}" \
    --allow-missing
  python3 "${ROOT}/tools/check-unified-opensearch-e2e-report.py" \
    "${UNIFIED_E2E_REPORT_DIR}/unified-opensearch-e2e-report.json" \
    --allow-missing
fi

if [[ "${RUN_REST_API_SOURCE_COVERAGE:-0}" == "1" ]]; then
  if [[ "${RUN_UNIFIED_E2E_REPORT:-0}" != "1" ]]; then
    echo "RUN_REST_API_SOURCE_COVERAGE=1 requires RUN_UNIFIED_E2E_REPORT=1" >&2
    exit 2
  fi
  python3 "${ROOT}/tools/report-rest-api-coverage.py" \
    --unified-report "${UNIFIED_E2E_REPORT_DIR}/unified-opensearch-e2e-report.json" \
    --require-live-required-suites \
    --min-live-required-matched-source-route-count "${REST_API_MIN_LIVE_REQUIRED_MATCHED_SOURCE_ROUTE_COUNT}" \
    --output "${REST_API_COVERAGE_REPORT}"
fi

echo "OpenSearch comparison completed"
echo "search compatibility report: ${REPORT_PATH}"
if [[ "${RUN_HTTP_LOAD_COMPARISON:-0}" == "1" ]]; then
  echo "load comparison report: ${LOAD_COMPARISON_REPORT}"
fi
if [[ "${RUN_ALIAS_TEMPLATE_PERSISTENCE_COMPARISON:-0}" == "1" ]]; then
  echo "alias/template persistence report: ${COMPARE_DIR}/alias-template-persistence-report.json"
fi
if [[ "${RUN_NATIVE_ROUTE_COVERAGE:-0}" == "1" ]]; then
  echo "native route fixture coverage report: ${NATIVE_ROUTE_FIXTURE_COVERAGE_REPORT}"
  echo "native route coverage report: ${NATIVE_ROUTE_COVERAGE_REPORT}"
fi
if [[ "${RUN_UNIFIED_E2E_REPORT:-0}" == "1" ]]; then
  echo "unified E2E report: ${UNIFIED_E2E_REPORT_DIR}/unified-opensearch-e2e-report.json"
fi
if [[ "${RUN_REST_API_SOURCE_COVERAGE:-0}" == "1" ]]; then
  echo "REST API source coverage report: ${REST_API_COVERAGE_REPORT}"
fi
