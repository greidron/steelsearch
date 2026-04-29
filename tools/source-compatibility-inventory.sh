#!/usr/bin/env bash
set -euo pipefail

OPENSEARCH_ROOT="${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}"
KNN_ROOT="${KNN_ROOT:-/home/ubuntu/k-NN}"
EXPECTED_OPENSEARCH_COMMIT="${EXPECTED_OPENSEARCH_COMMIT:-f991609d190dfd91c8a09902053a7bbfe0c27b3e}"
EXPECTED_KNN_COMMIT="${EXPECTED_KNN_COMMIT:-86ad5668acddbcf57d62ee0a3db17385aa93fde0}"

require_tool() {
  local tool="$1"
  if ! command -v "${tool}" >/dev/null 2>&1; then
    echo "missing required tool: ${tool}" >&2
    exit 127
  fi
}

require_file() {
  local file="$1"
  if [[ ! -f "${file}" ]]; then
    echo "missing source file: ${file}" >&2
    exit 2
  fi
}

repo_commit() {
  git -C "$1" rev-parse HEAD
}

assert_commit() {
  local label="$1"
  local root="$2"
  local expected="$3"
  local actual
  actual="$(repo_commit "${root}")"
  if [[ "${actual}" != "${expected}" ]]; then
    echo "${label} commit mismatch" >&2
    echo "  root:     ${root}" >&2
    echo "  expected: ${expected}" >&2
    echo "  actual:   ${actual}" >&2
    exit 3
  fi
}

count_rg() {
  local pattern="$1"
  shift
  rg -c "${pattern}" "$@" 2>/dev/null | awk -F: '{sum += $NF} END {print sum + 0}'
}

count_matching_files() {
  local pattern="$1"
  shift
  rg -l "${pattern}" "$@" 2>/dev/null | wc -l | tr -d ' '
}

require_tool git
require_tool rg
require_tool awk

ACTION_MODULE="${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/action/ActionModule.java"
SEARCH_MODULE="${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/search/SearchModule.java"
CLUSTER_MODULE="${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/cluster/ClusterModule.java"
INDICES_MODULE="${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/indices/IndicesModule.java"
INGEST_SERVICE="${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/ingest/IngestService.java"
SCRIPT_MODULE="${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/script/ScriptModule.java"
REPOSITORIES_MODULE="${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/repositories/RepositoriesModule.java"
KNN_PLUGIN="${KNN_ROOT}/src/main/java/org/opensearch/knn/plugin/KNNPlugin.java"
KNN_REST_DIR="${KNN_ROOT}/src/main/java/org/opensearch/knn/plugin/rest"

for file in \
  "${ACTION_MODULE}" \
  "${SEARCH_MODULE}" \
  "${CLUSTER_MODULE}" \
  "${INDICES_MODULE}" \
  "${INGEST_SERVICE}" \
  "${SCRIPT_MODULE}" \
  "${REPOSITORIES_MODULE}" \
  "${KNN_PLUGIN}"
do
  require_file "${file}"
done

if [[ ! -d "${KNN_REST_DIR}" ]]; then
  echo "missing source directory: ${KNN_REST_DIR}" >&2
  exit 2
fi

assert_commit "OpenSearch" "${OPENSEARCH_ROOT}" "${EXPECTED_OPENSEARCH_COMMIT}"
assert_commit "k-NN" "${KNN_ROOT}" "${EXPECTED_KNN_COMMIT}"

cat <<REPORT
# Source Compatibility Inventory Counts

OpenSearch root: ${OPENSEARCH_ROOT}
OpenSearch commit: $(repo_commit "${OPENSEARCH_ROOT}")
k-NN root: ${KNN_ROOT}
k-NN commit: $(repo_commit "${KNN_ROOT}")

| Surface | Source | Count |
| --- | --- | ---: |
| Core transport action registrations | ActionModule actions.register(...) | $(count_rg 'actions\.register\(' "${ACTION_MODULE}") |
| Core REST handler registrations | ActionModule registerHandler.accept(...) | $(count_rg 'registerHandler\.accept\(' "${ACTION_MODULE}") |
| Search query registrations | SearchModule registerQuery(...) | $(count_rg 'registerQuery\(' "${SEARCH_MODULE}") |
| Search aggregation registrations | SearchModule registerAggregation(...) | $(count_rg 'registerAggregation\(' "${SEARCH_MODULE}") |
| Search pipeline aggregation registrations | SearchModule registerPipelineAggregation(...) | $(count_rg 'registerPipelineAggregation\(' "${SEARCH_MODULE}") |
| Search suggester registrations | SearchModule registerSuggester(...) | $(count_rg 'registerSuggester\(' "${SEARCH_MODULE}") |
| Search score function registrations | SearchModule registerScoreFunction(...) | $(count_rg 'registerScoreFunction\(' "${SEARCH_MODULE}") |
| Search fetch sub-phase registrations | SearchModule registerFetchSubPhase(...) | $(count_rg 'registerFetchSubPhase\(' "${SEARCH_MODULE}") |
| Cluster custom registrations | ClusterModule registerClusterCustom(...) | $(count_rg 'registerClusterCustom\(' "${CLUSTER_MODULE}") |
| Metadata custom registrations | ClusterModule registerMetadataCustom(...) | $(count_rg 'registerMetadataCustom\(' "${CLUSTER_MODULE}") |
| Built-in mapper registrations | IndicesModule mappers.put(...) | $(count_rg 'mappers\.put\(' "${INDICES_MODULE}") |
| Built-in metadata mapper registrations | IndicesModule builtInMetadataMappers.put(...) | $(count_rg 'builtInMetadataMappers\.put\(' "${INDICES_MODULE}") |
| Ingest processor plugin hook sites | IngestService getProcessors(...) | $(count_rg 'getProcessors\(' "${INGEST_SERVICE}") |
| Script engine plugin hook sites | ScriptModule getScriptEngine(...) | $(count_rg 'getScriptEngine\(' "${SCRIPT_MODULE}") |
| Repository plugin hook sites | RepositoriesModule getRepositories(...) | $(count_rg 'getRepositories\(' "${REPOSITORIES_MODULE}") |
| k-NN transport action handlers | KNNPlugin new ActionHandler<>(...) | $(count_rg 'new ActionHandler<>' "${KNN_PLUGIN}") |
| k-NN REST routes | k-NN REST handlers new Route(...) | $(count_rg 'new Route\(' "${KNN_REST_DIR}"/*.java) |
| k-NN REST handler classes | k-NN REST handlers containing routes | $(count_matching_files 'new Route\(' "${KNN_REST_DIR}"/*.java) |

REPORT
