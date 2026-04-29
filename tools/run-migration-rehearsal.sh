#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'USAGE'
Run the migration rehearsal portion of the development replacement workflow.

This delegates to tools/run-development-replacement-rehearsal.sh, which starts
missing Steelsearch/OpenSearch endpoints, runs the shared compatibility fixture,
and writes MIGRATION_VALIDATION_REPORT.

Environment:
  MIGRATION_VALIDATION_REPORT  Migration validation report path.
  SEARCH_COMPAT_REPORT         Source search compatibility report path.
  STEELSEARCH_URL              Reuse an existing Steelsearch endpoint.
  OPENSEARCH_URL               Reuse an existing OpenSearch endpoint.
USAGE
  exit 0
fi

exec "${ROOT}/tools/run-development-replacement-rehearsal.sh" "$@"
