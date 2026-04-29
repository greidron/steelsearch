#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENSEARCH_ROOT="${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}"
KNN_ROOT="${KNN_ROOT:-/home/ubuntu/k-NN}"
OUT_DIR="${OUT_DIR:-${ROOT}/docs/rust-port/generated}"
EXPECTED_OPENSEARCH_COMMIT="${EXPECTED_OPENSEARCH_COMMIT:-f991609d190dfd91c8a09902053a7bbfe0c27b3e}"
EXPECTED_KNN_COMMIT="${EXPECTED_KNN_COMMIT:-86ad5668acddbcf57d62ee0a3db17385aa93fde0}"

require_tool() {
  local tool="$1"
  if ! command -v "${tool}" >/dev/null 2>&1; then
    echo "missing required tool: ${tool}" >&2
    exit 127
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

route_status() {
  local source="$1"
  local method="$2"
  local path="$3"

  if [[ "${source}" == "${KNN_ROOT}"/* ]]; then
    echo "planned"
    return
  fi

  if [[ "${source}" == "${OPENSEARCH_ROOT}/plugins/"* ]]; then
    echo "out-of-scope"
    return
  fi

  case "${method} ${path}" in
    "GET /"|"HEAD /")
      echo "implemented"
      ;;
    "GET /_cluster/health"|"PUT /{index}"|"GET /{index}"|"DELETE /{index}"|"PUT /{index}/_doc/{id}"|"GET /{index}/_doc/{id}")
      echo "stubbed"
      ;;
    *)
      echo "planned"
      ;;
  esac
}

action_status() {
  local source="$1"
  local action="$2"

  if [[ "${source}" == "${KNN_ROOT}"/* ]]; then
    echo "planned"
    return
  fi

  case "${action}" in
    *Recovery*|*SegmentReplication*)
      echo "planned"
      ;;
    *)
      echo "planned"
      ;;
  esac
}

extract_search_registrations() {
  local output="$1"
  {
    printf 'status\tcategory\texpression\tsource\tline\n'
    perl -0777 -ne '
      while (/(registerQuery|registerAggregation|registerPipelineAggregation|registerSuggester|registerScoreFunction|registerFetchSubPhase)\s*\(((?:[^()]++|\((?-1)?\))*)\)/sg) {
        my $kind = $1;
        my $args = $2;
        my $prefix = substr($_, 0, $-[0]);
        my $line = 1 + ($prefix =~ tr/\n//);
        $args =~ s/\s+/ /g;
        $args =~ s/^\s+|\s+$//g;
        print "$kind\t$args\t$line\n";
      }
    ' "${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/search/SearchModule.java" |
      while IFS=$'\t' read -r kind text line; do
        local category status
        case "${kind}" in
          registerQuery) category="query" ;;
          registerAggregation) category="aggregation" ;;
          registerPipelineAggregation) category="pipeline_aggregation" ;;
          registerSuggester) category="suggester" ;;
          registerScoreFunction) category="score_function" ;;
          registerFetchSubPhase) category="fetch_subphase" ;;
          *) category="other" ;;
        esac
        status="planned"
        printf '%s\t%s\t%s\t%s\t%s\n' "${status}" "${category}" "${text}" "${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/search/SearchModule.java" "${line}"
      done
  } >"${output}"
}

extract_node_runtime_components() {
  local output="$1"
  {
    printf 'status\tkind\tcomponent\tsource\tline\n'
    perl -0777 -ne '
      while (/new\s+([A-Za-z0-9_]+(?:Module|Service|Gateway|Coordinator|Controller|Registry))\s*\(/sg) {
        my $component = $1;
        my $prefix = substr($_, 0, $-[0]);
        my $line = 1 + ($prefix =~ tr/\n//);
        print "$component\t$line\n";
      }
    ' "${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/node/Node.java" |
      while IFS=$'\t' read -r component line; do
        local kind status
        case "${component}" in
          *Module) kind="module" ;;
          *Service) kind="service" ;;
          *Gateway) kind="gateway" ;;
          *Coordinator) kind="coordinator" ;;
          *Controller) kind="controller" ;;
          *Registry) kind="registry" ;;
          *) kind="component" ;;
        esac
        status="planned"
        printf '%s\t%s\t%s\t%s\t%s\n' "${status}" "${kind}" "${component}" "${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/node/Node.java" "${line}"
      done
  } >"${output}"
}

build_compatibility_matrix() {
  local output="$1"
  local rest_routes="$2"
  local transport_actions="$3"
  local search_registrations="$4"
  local node_runtime_components="$5"

  {
    printf 'surface\tstatus\tcategory\tidentifier\tdetail\tsource\tline\n'
    awk -F '\t' 'NR > 1 { printf "rest_route\t%s\t%s\t%s\t\t%s\t%s\n", $1, $2, $3, $4, $5 }' "${rest_routes}"
    awk -F '\t' 'NR > 1 { printf "transport_action\t%s\taction\t%s\t%s\t%s\t%s\n", $1, $2, $3, $4, $5 }' "${transport_actions}"
    awk -F '\t' 'NR > 1 { printf "search_registration\t%s\t%s\t%s\t\t%s\t%s\n", $1, $2, $3, $4, $5 }' "${search_registrations}"
    awk -F '\t' 'NR > 1 { printf "node_runtime\t%s\t%s\t%s\t\t%s\t%s\n", $1, $2, $3, $4, $5 }' "${node_runtime_components}"
  } >"${output}"
}

extract_rest_routes() {
  local output="$1"
  {
    printf 'status\tmethod\tpath_or_expression\tsource\tline\n'
    {
      rg -l 'new Route\(' \
        "${OPENSEARCH_ROOT}/server/src/main/java" \
        "${OPENSEARCH_ROOT}/modules" \
        "${OPENSEARCH_ROOT}/plugins" \
        "${KNN_ROOT}/src/main/java" |
        while IFS= read -r file; do
          perl -0777 -ne '
            while (/new\s+Route\s*\(\s*([^,\n]+?)\s*,\s*((?:String\.format\((?:[^()]|\([^()]*\))*\))|(?:"(?:\\.|[^"])*"(?:\s*\+\s*[^,\n)]+)*)|[^)\n]+?)\s*\)/sg) {
              my $method = $1;
              my $path = $2;
              $method =~ s/^\s+|\s+$//g;
              $path =~ s/^\s+|\s+$//g;
              my $prefix = substr($_, 0, $-[0]);
              my $line = 1 + ($prefix =~ tr/\n//);
              $method =~ s/\t/ /g;
              $path =~ s/\t/ /g;
              print "$method\t$path\t$line\n";
            }
          ' "${file}" |
            while IFS=$'\t' read -r method path_expr line; do
              local path_clean status
              method="$(printf '%s' "${method}" | sed -E 's/.*RestRequest\.Method\.//; s/.*Method\.//; s/[^A-Z_].*$//; s/^[[:space:]]+//; s/[[:space:]]+$//')"
              path_expr="$(printf '%s' "${path_expr}" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
              path_clean="${path_expr}"
              if [[ "${path_clean}" =~ ^\".*\"$ ]]; then
                path_clean="${path_clean:1:${#path_clean}-2}"
              fi
              status="$(route_status "${file}" "${method}" "${path_clean}")"
              printf '%s\t%s\t%s\t%s\t%s\n' "${status}" "${method}" "${path_clean}" "${file}" "${line}"
            done
        done
    } | sort -t $'\t' -k4,4 -k5,5n -k2,2 -k3,3
  } >"${output}"
}

extract_transport_actions() {
  local output="$1"
  {
    printf 'status\taction\ttransport_handler\tsource\tline\n'
    perl -0777 -ne '
      while (/actions\.register\(\s*([^,;]+?)\s*,\s*([^,;)]+)(?:,|\))/sg) {
        my $action = $1;
        my $handler = $2;
        $action =~ s/\s+//g;
        $handler =~ s/\s+//g;
        my $prefix = substr($_, 0, $-[0]);
        my $line = 1 + ($prefix =~ tr/\n//);
        print "$action\t$handler\t$line\n";
      }
    ' "${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/action/ActionModule.java" |
      while IFS=$'\t' read -r action handler line; do
        local source="${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/action/ActionModule.java"
        printf '%s\t%s\t%s\t%s\t%s\n' "$(action_status "${source}" "${action}")" "${action}" "${handler}" "${source}" "${line}"
      done

    perl -0777 -ne '
      while (/new ActionHandler<>\(\s*([^,;]+?)\s*,\s*([^,)]+)\)/sg) {
        my $action = $1;
        my $handler = $2;
        $action =~ s/\s+//g;
        $handler =~ s/\s+//g;
        my $prefix = substr($_, 0, $-[0]);
        my $line = 1 + ($prefix =~ tr/\n//);
        print "$action\t$handler\t$line\n";
      }
    ' "${KNN_ROOT}/src/main/java/org/opensearch/knn/plugin/KNNPlugin.java" |
      while IFS=$'\t' read -r action handler line; do
        local source="${KNN_ROOT}/src/main/java/org/opensearch/knn/plugin/KNNPlugin.java"
        printf '%s\t%s\t%s\t%s\t%s\n' "$(action_status "${source}" "${action}")" "${action}" "${handler}" "${source}" "${line}"
      done
  } >"${output}"
}

require_tool git
require_tool perl
require_tool rg
require_tool sed

assert_commit "OpenSearch" "${OPENSEARCH_ROOT}" "${EXPECTED_OPENSEARCH_COMMIT}"
assert_commit "k-NN" "${KNN_ROOT}" "${EXPECTED_KNN_COMMIT}"

mkdir -p "${OUT_DIR}"
REST_ROUTES_OUT="${OUT_DIR}/source-rest-routes.tsv"
TRANSPORT_ACTIONS_OUT="${OUT_DIR}/source-transport-actions.tsv"
SEARCH_REGISTRATIONS_OUT="${OUT_DIR}/source-search-registrations.tsv"
NODE_RUNTIME_COMPONENTS_OUT="${OUT_DIR}/source-node-runtime-components.tsv"
COMPATIBILITY_MATRIX_OUT="${OUT_DIR}/source-compatibility-matrix.tsv"

extract_rest_routes "${REST_ROUTES_OUT}"
extract_transport_actions "${TRANSPORT_ACTIONS_OUT}"
extract_search_registrations "${SEARCH_REGISTRATIONS_OUT}"
extract_node_runtime_components "${NODE_RUNTIME_COMPONENTS_OUT}"
build_compatibility_matrix \
  "${COMPATIBILITY_MATRIX_OUT}" \
  "${REST_ROUTES_OUT}" \
  "${TRANSPORT_ACTIONS_OUT}" \
  "${SEARCH_REGISTRATIONS_OUT}" \
  "${NODE_RUNTIME_COMPONENTS_OUT}"

echo "generated ${REST_ROUTES_OUT}"
echo "generated ${TRANSPORT_ACTIONS_OUT}"
echo "generated ${SEARCH_REGISTRATIONS_OUT}"
echo "generated ${NODE_RUNTIME_COMPONENTS_OUT}"
echo "generated ${COMPATIBILITY_MATRIX_OUT}"
