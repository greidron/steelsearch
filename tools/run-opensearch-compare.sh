#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPARE_DIR="${COMPARE_DIR:-${ROOT}/target/opensearch-compare}"
REPORT_PATH="${SEARCH_COMPAT_REPORT:-${COMPARE_DIR}/search-compat-report.json}"
LOAD_COMPARISON_REPORT="${STEELSEARCH_LOAD_COMPARISON_REPORT:-${COMPARE_DIR}/http-load-comparison.json}"

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
  RUN_ALIAS_TEMPLATE_PERSISTENCE_COMPARISON=1
                                    Include the alias/template persistence
                                    live parity report.
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

echo "OpenSearch comparison completed"
echo "search compatibility report: ${REPORT_PATH}"
if [[ "${RUN_HTTP_LOAD_COMPARISON:-0}" == "1" ]]; then
  echo "load comparison report: ${LOAD_COMPARISON_REPORT}"
fi
if [[ "${RUN_ALIAS_TEMPLATE_PERSISTENCE_COMPARISON:-0}" == "1" ]]; then
  echo "alias/template persistence report: ${COMPARE_DIR}/alias-template-persistence-report.json"
fi
