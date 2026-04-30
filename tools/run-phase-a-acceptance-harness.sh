#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="local"
WORK_DIR=""
SCOPE="full"
PASSTHRU=()

usage() {
  cat <<'USAGE'
Run the Phase A Steelsearch/OpenSearch acceptance harness entrypoint.

Usage:
  tools/run-phase-a-acceptance-harness.sh [--mode local|ci] [--scope full|root-cluster-node|index-metadata|document-write-path|search|search-execution|snapshot-migration|vector-ml|transport-admin] [--work-dir DIR] [args...]

Modes:
  local   Default. Writes reusable reports under target/phase-a-acceptance-harness/local.
  ci      Writes reusable reports under target/phase-a-acceptance-harness/ci and exports CI=true.

Scopes:
  full               Default. Runs the full Phase A compare tree.
  root-cluster-node  Runs the runtime-backed root/cluster/node compare subset as a first-class preset.
  index-metadata     Runs the runtime-backed index lifecycle/metadata compare subset as a first-class preset.
  document-write-path
                     Runs the runtime-backed document/write-path compare subset as a first-class preset.
  search             Runs the runtime-backed search compare subset as a first-class preset.
  search-execution   Runs the runtime-backed multi-shard search execution/accounting subset as a first-class preset.
  snapshot-migration Runs the runtime-backed snapshot/migration compare subset as a first-class preset.
  vector-ml          Runs the runtime-backed vector/ML compare subset as a first-class preset.
  transport-admin    Runs the runtime-backed standalone transport/admin subset as a first-class preset.

Environment passthrough:
  STEELSEARCH_URL                   Reuse an existing Steelsearch endpoint.
  OPENSEARCH_URL                    Reuse an existing OpenSearch endpoint.
  RUN_RUNTIME_PRECHECK=0            Skip the `cargo check -p os-node --features standalone-runtime --bin steelsearch` preflight gate.
  RUN_CLUSTER_HEALTH_COMPAT=0       Skip the always-on cluster health live comparison.
  RUN_ALLOCATION_EXPLAIN_COMPAT=0   Skip the always-on allocation explain live comparison.
  RUN_CLUSTER_SETTINGS_COMPAT=0     Skip the always-on cluster settings live comparison.
  RUN_CLUSTER_STATE_COMPAT=0        Skip the always-on cluster state live comparison.
  RUN_ROOT_CLUSTER_NODE_COMPAT=0    Skip the always-on root route live comparison.
  RUN_TASKS_COMPAT=0                Skip the always-on task/pending-task live comparison.
  RUN_STATS_COMPAT=0                Skip the always-on stats live comparison.
  RUN_INDEX_LIFECYCLE_COMPAT=0      Skip the always-on index lifecycle live comparison.
  RUN_MAPPING_COMPAT=0              Skip the always-on mapping live comparison.
  RUN_SETTINGS_COMPAT=0             Skip the always-on index settings live comparison.
  RUN_SINGLE_DOC_CRUD_COMPAT=0      Skip the always-on single-document CRUD comparison.
  RUN_REFRESH_COMPAT=0              Skip the always-on refresh visibility comparison.
  RUN_BULK_COMPAT=0                 Skip the always-on bulk partial-failure comparison.
  RUN_ROUTING_COMPAT=0              Skip the always-on custom-routing visibility comparison.
  RUN_ALIAS_READ_COMPAT=0           Skip the always-on alias read live comparison.
  RUN_TEMPLATE_COMPAT=0             Skip the always-on template live comparison.
  RUN_SNAPSHOT_LIFECYCLE_COMPAT=0   Skip the always-on snapshot lifecycle comparison.
  RUN_DATA_STREAM_ROLLOVER_COMPAT=0 Skip the always-on data-stream/rollover comparison.
  RUN_MIGRATION_CUTOVER_INTEGRATION=1
                                    Also run the OpenSearch->Steelsearch cutover integration.
  RUN_VECTOR_SEARCH_COMPAT=1        Also run the bounded vector/hybrid search comparison.
  RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=1
                                    Also run the Steelsearch-only multi-node transport/admin integration.
  RUN_HTTP_LOAD_COMPARISON=1        Also run HTTP load comparison.
  RUN_ALIAS_TEMPLATE_PERSISTENCE_COMPARISON=1
                                    Also run alias/template persistence comparison.

All remaining arguments are passed to tools/run-opensearch-compare.sh.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --work-dir)
      WORK_DIR="${2:-}"
      shift 2
      ;;
    --scope)
      SCOPE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      PASSTHRU+=("$1")
      shift
      ;;
  esac
done

case "${MODE}" in
  local|ci) ;;
  *)
    echo "Unsupported mode: ${MODE}" >&2
    usage >&2
    exit 2
    ;;
esac

case "${SCOPE}" in
  full|root-cluster-node|index-metadata|document-write-path|search|search-execution|snapshot-migration|vector-ml|transport-admin) ;;
  *)
    echo "Unsupported scope: ${SCOPE}" >&2
    usage >&2
    exit 2
    ;;
esac

if [[ -z "${WORK_DIR}" ]]; then
  WORK_DIR="${ROOT}/target/phase-a-acceptance-harness/${MODE}"
fi

mkdir -p "${WORK_DIR}"
export COMPARE_DIR="${COMPARE_DIR:-${WORK_DIR}/compare}"
export REHEARSAL_DIR="${REHEARSAL_DIR:-${WORK_DIR}/rehearsal}"
mkdir -p "${COMPARE_DIR}" "${REHEARSAL_DIR}"
export RUNTIME_PRECHECK_REPORT="${RUNTIME_PRECHECK_REPORT:-${COMPARE_DIR}/runtime-precheck-report.json}"
export GENERATED_API_SPEC_REPORT="${GENERATED_API_SPEC_REPORT:-${COMPARE_DIR}/generated-api-spec-report.json}"
export SEARCH_COMPAT_REPORT="${SEARCH_COMPAT_REPORT:-${COMPARE_DIR}/search-compat-report.json}"
export CLUSTER_HEALTH_COMPAT_REPORT="${CLUSTER_HEALTH_COMPAT_REPORT:-${COMPARE_DIR}/cluster-health-compat-report.json}"
export ALLOCATION_EXPLAIN_COMPAT_REPORT="${ALLOCATION_EXPLAIN_COMPAT_REPORT:-${COMPARE_DIR}/allocation-explain-compat-report.json}"
export CLUSTER_SETTINGS_COMPAT_REPORT="${CLUSTER_SETTINGS_COMPAT_REPORT:-${COMPARE_DIR}/cluster-settings-compat-report.json}"
export CLUSTER_STATE_COMPAT_REPORT="${CLUSTER_STATE_COMPAT_REPORT:-${COMPARE_DIR}/cluster-state-compat-report.json}"
export ROOT_CLUSTER_NODE_COMPAT_REPORT="${ROOT_CLUSTER_NODE_COMPAT_REPORT:-${COMPARE_DIR}/root-cluster-node-compat-report.json}"
export TASKS_COMPAT_REPORT="${TASKS_COMPAT_REPORT:-${COMPARE_DIR}/tasks-compat-report.json}"
export STATS_COMPAT_REPORT="${STATS_COMPAT_REPORT:-${COMPARE_DIR}/stats-compat-report.json}"
export INDEX_LIFECYCLE_COMPAT_REPORT="${INDEX_LIFECYCLE_COMPAT_REPORT:-${COMPARE_DIR}/index-lifecycle-compat-report.json}"
export MAPPING_COMPAT_REPORT="${MAPPING_COMPAT_REPORT:-${COMPARE_DIR}/mapping-compat-report.json}"
export SETTINGS_COMPAT_REPORT="${SETTINGS_COMPAT_REPORT:-${COMPARE_DIR}/settings-compat-report.json}"
export SINGLE_DOC_CRUD_COMPAT_REPORT="${SINGLE_DOC_CRUD_COMPAT_REPORT:-${COMPARE_DIR}/single-doc-crud-compat-report.json}"
export REFRESH_COMPAT_REPORT="${REFRESH_COMPAT_REPORT:-${COMPARE_DIR}/refresh-compat-report.json}"
export BULK_COMPAT_REPORT="${BULK_COMPAT_REPORT:-${COMPARE_DIR}/bulk-compat-report.json}"
export ROUTING_COMPAT_REPORT="${ROUTING_COMPAT_REPORT:-${COMPARE_DIR}/routing-compat-report.json}"
export ALIAS_READ_COMPAT_REPORT="${ALIAS_READ_COMPAT_REPORT:-${COMPARE_DIR}/alias-read-compat-report.json}"
export TEMPLATE_COMPAT_REPORT="${TEMPLATE_COMPAT_REPORT:-${COMPARE_DIR}/template-compat-report.json}"
export SNAPSHOT_LIFECYCLE_COMPAT_REPORT="${SNAPSHOT_LIFECYCLE_COMPAT_REPORT:-${COMPARE_DIR}/snapshot-lifecycle-compat-report.json}"
export DATA_STREAM_ROLLOVER_COMPAT_REPORT="${DATA_STREAM_ROLLOVER_COMPAT_REPORT:-${COMPARE_DIR}/data-stream-rollover-compat-report.json}"
export MIGRATION_CUTOVER_INTEGRATION_REPORT="${MIGRATION_CUTOVER_INTEGRATION_REPORT:-${COMPARE_DIR}/migration-cutover-integration-report.json}"
export VECTOR_SEARCH_COMPAT_REPORT="${VECTOR_SEARCH_COMPAT_REPORT:-${COMPARE_DIR}/vector-search-compat-report.json}"
export ML_MODEL_SURFACE_COMPAT_REPORT="${ML_MODEL_SURFACE_COMPAT_REPORT:-${COMPARE_DIR}/ml-model-surface-compat-report.json}"
export MULTI_NODE_TRANSPORT_ADMIN_REPORT="${MULTI_NODE_TRANSPORT_ADMIN_REPORT:-${COMPARE_DIR}/multi-node-transport-admin-report.json}"
export SNAPSHOT_REPOSITORY_BASE_DIR="${SNAPSHOT_REPOSITORY_BASE_DIR:-${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}/build/testclusters/runTask-0/repo}"
export RUN_GENERATED_API_SPEC_CHECK="${RUN_GENERATED_API_SPEC_CHECK:-1}"
export RUN_RUNTIME_PRECHECK="${RUN_RUNTIME_PRECHECK:-1}"
export RUN_OPENSEARCH_COMPARISON="${RUN_OPENSEARCH_COMPARISON:-1}"
export RUN_CLUSTER_HEALTH_COMPAT="${RUN_CLUSTER_HEALTH_COMPAT:-1}"
export RUN_ALLOCATION_EXPLAIN_COMPAT="${RUN_ALLOCATION_EXPLAIN_COMPAT:-1}"
export RUN_CLUSTER_SETTINGS_COMPAT="${RUN_CLUSTER_SETTINGS_COMPAT:-1}"
export RUN_CLUSTER_STATE_COMPAT="${RUN_CLUSTER_STATE_COMPAT:-1}"
export RUN_ROOT_CLUSTER_NODE_COMPAT="${RUN_ROOT_CLUSTER_NODE_COMPAT:-1}"
export RUN_TASKS_COMPAT="${RUN_TASKS_COMPAT:-1}"
export RUN_STATS_COMPAT="${RUN_STATS_COMPAT:-1}"
export RUN_INDEX_LIFECYCLE_COMPAT="${RUN_INDEX_LIFECYCLE_COMPAT:-1}"
export RUN_MAPPING_COMPAT="${RUN_MAPPING_COMPAT:-1}"
export RUN_SETTINGS_COMPAT="${RUN_SETTINGS_COMPAT:-1}"
export RUN_SINGLE_DOC_CRUD_COMPAT="${RUN_SINGLE_DOC_CRUD_COMPAT:-1}"
export RUN_REFRESH_COMPAT="${RUN_REFRESH_COMPAT:-1}"
export RUN_BULK_COMPAT="${RUN_BULK_COMPAT:-1}"
export RUN_ROUTING_COMPAT="${RUN_ROUTING_COMPAT:-1}"
export RUN_ALIAS_READ_COMPAT="${RUN_ALIAS_READ_COMPAT:-1}"
export RUN_TEMPLATE_COMPAT="${RUN_TEMPLATE_COMPAT:-1}"
export RUN_SNAPSHOT_LIFECYCLE_COMPAT="${RUN_SNAPSHOT_LIFECYCLE_COMPAT:-1}"
export RUN_DATA_STREAM_ROLLOVER_COMPAT="${RUN_DATA_STREAM_ROLLOVER_COMPAT:-1}"
export RUN_MIGRATION_CUTOVER_INTEGRATION="${RUN_MIGRATION_CUTOVER_INTEGRATION:-0}"
export RUN_VECTOR_SEARCH_COMPAT="${RUN_VECTOR_SEARCH_COMPAT:-0}"
export RUN_ML_MODEL_SURFACE_COMPAT="${RUN_ML_MODEL_SURFACE_COMPAT:-0}"
export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION="${RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION:-0}"
export PHASE_A_COMPARE_SCOPE="${PHASE_A_COMPARE_SCOPE:-${SCOPE}}"

if [[ "${PHASE_A_COMPARE_SCOPE}" == "search-execution" ]]; then
  export SEARCH_COMPAT_FIXTURE="${SEARCH_COMPAT_FIXTURE:-${ROOT}/tools/fixtures/search-execution-compat.json}"
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "search" ]]; then
  export SEARCH_COMPAT_FIXTURE="${SEARCH_COMPAT_FIXTURE:-${ROOT}/tools/fixtures/search-strict-compat.json}"
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "full" ]]; then
  export SEARCH_COMPAT_FIXTURE="${SEARCH_COMPAT_FIXTURE:-${ROOT}/tools/fixtures/search-strict-compat.json}"
  export SEARCH_COMPAT_EXCLUDE_CASES="${SEARCH_COMPAT_EXCLUDE_CASES:-expand_wildcards_closed_fail_closed,get_aliases_readback,cat_count_json,cat_count_text}"
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "root-cluster-node" ]]; then
  export RUN_SEARCH_COMPAT=0
  export RUN_INDEX_LIFECYCLE_COMPAT=0
  export RUN_MAPPING_COMPAT=0
  export RUN_SETTINGS_COMPAT=0
  export RUN_SINGLE_DOC_CRUD_COMPAT=0
  export RUN_REFRESH_COMPAT=0
  export RUN_BULK_COMPAT=0
  export RUN_ROUTING_COMPAT=0
  export RUN_ALIAS_READ_COMPAT=0
  export RUN_TEMPLATE_COMPAT=0
  export RUN_SNAPSHOT_LIFECYCLE_COMPAT=0
  export RUN_DATA_STREAM_ROLLOVER_COMPAT=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION=0
  export RUN_VECTOR_SEARCH_COMPAT=0
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=0
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "index-metadata" ]]; then
  export RUN_SEARCH_COMPAT=0
  export RUN_CLUSTER_HEALTH_COMPAT=0
  export RUN_ALLOCATION_EXPLAIN_COMPAT=0
  export RUN_CLUSTER_SETTINGS_COMPAT=0
  export RUN_CLUSTER_STATE_COMPAT=0
  export RUN_ROOT_CLUSTER_NODE_COMPAT=0
  export RUN_TASKS_COMPAT=0
  export RUN_STATS_COMPAT=0
  export RUN_SINGLE_DOC_CRUD_COMPAT=0
  export RUN_REFRESH_COMPAT=0
  export RUN_BULK_COMPAT=0
  export RUN_ROUTING_COMPAT=0
  export RUN_SNAPSHOT_LIFECYCLE_COMPAT=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION=0
  export RUN_VECTOR_SEARCH_COMPAT=0
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=0
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "document-write-path" ]]; then
  export RUN_SEARCH_COMPAT=0
  export RUN_CLUSTER_HEALTH_COMPAT=0
  export RUN_ALLOCATION_EXPLAIN_COMPAT=0
  export RUN_CLUSTER_SETTINGS_COMPAT=0
  export RUN_CLUSTER_STATE_COMPAT=0
  export RUN_ROOT_CLUSTER_NODE_COMPAT=0
  export RUN_TASKS_COMPAT=0
  export RUN_STATS_COMPAT=0
  export RUN_INDEX_LIFECYCLE_COMPAT=0
  export RUN_MAPPING_COMPAT=0
  export RUN_SETTINGS_COMPAT=0
  export RUN_ALIAS_READ_COMPAT=0
  export RUN_TEMPLATE_COMPAT=0
  export RUN_SNAPSHOT_LIFECYCLE_COMPAT=0
  export RUN_DATA_STREAM_ROLLOVER_COMPAT=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION=0
  export RUN_VECTOR_SEARCH_COMPAT=0
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=0
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "search" ]]; then
  export RUN_CLUSTER_HEALTH_COMPAT=0
  export RUN_ALLOCATION_EXPLAIN_COMPAT=0
  export RUN_CLUSTER_SETTINGS_COMPAT=0
  export RUN_CLUSTER_STATE_COMPAT=0
  export RUN_ROOT_CLUSTER_NODE_COMPAT=0
  export RUN_TASKS_COMPAT=0
  export RUN_STATS_COMPAT=0
  export RUN_INDEX_LIFECYCLE_COMPAT=0
  export RUN_MAPPING_COMPAT=0
  export RUN_SETTINGS_COMPAT=0
  export RUN_SINGLE_DOC_CRUD_COMPAT=0
  export RUN_REFRESH_COMPAT=0
  export RUN_BULK_COMPAT=0
  export RUN_ROUTING_COMPAT=0
  export RUN_ALIAS_READ_COMPAT=0
  export RUN_TEMPLATE_COMPAT=0
  export RUN_SNAPSHOT_LIFECYCLE_COMPAT=0
  export RUN_DATA_STREAM_ROLLOVER_COMPAT=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION=0
  export RUN_VECTOR_SEARCH_COMPAT=0
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=0
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "search-execution" ]]; then
  export RUN_CLUSTER_HEALTH_COMPAT=0
  export RUN_ALLOCATION_EXPLAIN_COMPAT=0
  export RUN_CLUSTER_SETTINGS_COMPAT=0
  export RUN_CLUSTER_STATE_COMPAT=0
  export RUN_ROOT_CLUSTER_NODE_COMPAT=0
  export RUN_TASKS_COMPAT=0
  export RUN_STATS_COMPAT=0
  export RUN_INDEX_LIFECYCLE_COMPAT=0
  export RUN_MAPPING_COMPAT=0
  export RUN_SETTINGS_COMPAT=0
  export RUN_SINGLE_DOC_CRUD_COMPAT=0
  export RUN_REFRESH_COMPAT=0
  export RUN_BULK_COMPAT=0
  export RUN_ROUTING_COMPAT=0
  export RUN_ALIAS_READ_COMPAT=0
  export RUN_TEMPLATE_COMPAT=0
  export RUN_SNAPSHOT_LIFECYCLE_COMPAT=0
  export RUN_DATA_STREAM_ROLLOVER_COMPAT=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION=0
  export RUN_VECTOR_SEARCH_COMPAT=0
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=0
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "snapshot-migration" ]]; then
  export RUN_CLUSTER_HEALTH_COMPAT=0
  export RUN_ALLOCATION_EXPLAIN_COMPAT=0
  export RUN_CLUSTER_SETTINGS_COMPAT=0
  export RUN_CLUSTER_STATE_COMPAT=0
  export RUN_ROOT_CLUSTER_NODE_COMPAT=0
  export RUN_TASKS_COMPAT=0
  export RUN_STATS_COMPAT=0
  export RUN_INDEX_LIFECYCLE_COMPAT=0
  export RUN_MAPPING_COMPAT=0
  export RUN_SETTINGS_COMPAT=0
  export RUN_SINGLE_DOC_CRUD_COMPAT=0
  export RUN_REFRESH_COMPAT=0
  export RUN_BULK_COMPAT=0
  export RUN_ROUTING_COMPAT=0
  export RUN_ALIAS_READ_COMPAT=0
  export RUN_TEMPLATE_COMPAT=0
  export RUN_DATA_STREAM_ROLLOVER_COMPAT=0
  export RUN_SEARCH_COMPAT=0
  export RUN_VECTOR_SEARCH_COMPAT=0
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION=1
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "vector-ml" ]]; then
  export RUN_CLUSTER_HEALTH_COMPAT=0
  export RUN_ALLOCATION_EXPLAIN_COMPAT=0
  export RUN_CLUSTER_SETTINGS_COMPAT=0
  export RUN_CLUSTER_STATE_COMPAT=0
  export RUN_ROOT_CLUSTER_NODE_COMPAT=0
  export RUN_TASKS_COMPAT=0
  export RUN_STATS_COMPAT=0
  export RUN_INDEX_LIFECYCLE_COMPAT=0
  export RUN_MAPPING_COMPAT=0
  export RUN_SETTINGS_COMPAT=0
  export RUN_SINGLE_DOC_CRUD_COMPAT=0
  export RUN_REFRESH_COMPAT=0
  export RUN_BULK_COMPAT=0
  export RUN_ROUTING_COMPAT=0
  export RUN_ALIAS_READ_COMPAT=0
  export RUN_TEMPLATE_COMPAT=0
  export RUN_SNAPSHOT_LIFECYCLE_COMPAT=0
  export RUN_DATA_STREAM_ROLLOVER_COMPAT=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION=0
  export RUN_SEARCH_COMPAT=0
  export RUN_VECTOR_SEARCH_COMPAT=1
  export RUN_ML_MODEL_SURFACE_COMPAT=1
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=0
fi

if [[ "${PHASE_A_COMPARE_SCOPE}" == "transport-admin" ]]; then
  export RUN_CLUSTER_HEALTH_COMPAT=0
  export RUN_ALLOCATION_EXPLAIN_COMPAT=0
  export RUN_CLUSTER_SETTINGS_COMPAT=0
  export RUN_CLUSTER_STATE_COMPAT=0
  export RUN_ROOT_CLUSTER_NODE_COMPAT=0
  export RUN_TASKS_COMPAT=0
  export RUN_STATS_COMPAT=0
  export RUN_INDEX_LIFECYCLE_COMPAT=0
  export RUN_MAPPING_COMPAT=0
  export RUN_SETTINGS_COMPAT=0
  export RUN_SINGLE_DOC_CRUD_COMPAT=0
  export RUN_REFRESH_COMPAT=0
  export RUN_BULK_COMPAT=0
  export RUN_ROUTING_COMPAT=0
  export RUN_ALIAS_READ_COMPAT=0
  export RUN_TEMPLATE_COMPAT=0
  export RUN_SNAPSHOT_LIFECYCLE_COMPAT=0
  export RUN_DATA_STREAM_ROLLOVER_COMPAT=0
  export RUN_MIGRATION_CUTOVER_INTEGRATION=0
  export RUN_SEARCH_COMPAT=0
  export RUN_VECTOR_SEARCH_COMPAT=0
  export RUN_MULTI_NODE_TRANSPORT_ADMIN_INTEGRATION=1
fi

if [[ "${MODE}" == "ci" ]]; then
  export CI="${CI:-true}"
fi

if [[ "${RUN_GENERATED_API_SPEC_CHECK}" != "0" ]]; then
  GENERATED_API_SPEC_LOG="${REHEARSAL_DIR}/generated-api-spec.log"
  GENERATED_API_SPEC_COMMAND="bash tools/check-generated-api-spec.sh"
  echo "Running generated API spec gate: ${GENERATED_API_SPEC_COMMAND}"
  if ${GENERATED_API_SPEC_COMMAND} >"${GENERATED_API_SPEC_LOG}" 2>&1; then
    cat >"${GENERATED_API_SPEC_REPORT}" <<EOF
{
  "kind": "generated-api-spec",
  "gate": "pass",
  "command": "${GENERATED_API_SPEC_COMMAND}",
  "log_path": "${GENERATED_API_SPEC_LOG}",
  "notes": [
    "Generated REST route reference, transport reference, route evidence matrix, and OpenAPI artifact are in sync.",
    "Release-auditable generated API spec drift test passed."
  ]
}
EOF
  else
    cat >"${GENERATED_API_SPEC_REPORT}" <<EOF
{
  "kind": "generated-api-spec",
  "gate": "fail",
  "command": "${GENERATED_API_SPEC_COMMAND}",
  "log_path": "${GENERATED_API_SPEC_LOG}",
  "notes": [
    "Generated API spec artifacts drifted from the checked-in versions or the release-auditable artifact test failed."
  ]
}
EOF
    echo "Generated API spec gate failed; see ${GENERATED_API_SPEC_LOG}" >&2
    exit 1
  fi
fi

if [[ "${RUN_RUNTIME_PRECHECK}" != "0" ]]; then
  RUNTIME_PRECHECK_LOG="${REHEARSAL_DIR}/cargo-check-os-node.log"
  RUNTIME_PRECHECK_COMMAND="cargo check -p os-node --features standalone-runtime --bin steelsearch"
  echo "Running runtime precheck: ${RUNTIME_PRECHECK_COMMAND}"
  if ${RUNTIME_PRECHECK_COMMAND} >"${RUNTIME_PRECHECK_LOG}" 2>&1; then
    cat >"${RUNTIME_PRECHECK_REPORT}" <<EOF
{
  "kind": "runtime-precheck",
  "compile_gate": "pass",
  "command": "${RUNTIME_PRECHECK_COMMAND}",
  "log_path": "${RUNTIME_PRECHECK_LOG}",
  "evidence_source": "runtime-backed preflight",
  "notes": [
    "Acceptance comparison may continue because the os-node crate compiled.",
    "Helper-only or local-harness-only evidence must still be distinguished from real SteelNode HTTP/runtime path results."
  ]
}
EOF
  else
    cat >"${RUNTIME_PRECHECK_REPORT}" <<EOF
{
  "kind": "runtime-precheck",
  "compile_gate": "fail",
  "command": "${RUNTIME_PRECHECK_COMMAND}",
  "log_path": "${RUNTIME_PRECHECK_LOG}",
  "evidence_source": "runtime-backed preflight",
  "notes": [
    "Acceptance comparison stopped before route execution because the os-node crate did not compile.",
    "Treat all helper-only or local-harness-only evidence as insufficient until this gate passes."
  ]
}
EOF
    echo "Runtime precheck failed; see ${RUNTIME_PRECHECK_LOG}" >&2
    exit 1
  fi
fi

exec "${ROOT}/tools/run-opensearch-compare.sh" "${PASSTHRU[@]}"
