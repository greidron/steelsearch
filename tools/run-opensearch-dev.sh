#!/usr/bin/env bash
set -euo pipefail

OPENSEARCH_ROOT="${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}"
HOST="${OPENSEARCH_HTTP_HOST:-127.0.0.1}"
TRANSPORT_HOST="${OPENSEARCH_TRANSPORT_HOST:-${HOST}}"
TRANSPORT_PUBLISH_HOST="${OPENSEARCH_TRANSPORT_PUBLISH_HOST:-}"
TRANSPORT_PUBLISH_PORT="${OPENSEARCH_TRANSPORT_PUBLISH_PORT:-}"
PING_SCHEDULE="${OPENSEARCH_PING_SCHEDULE:-}"
TRANSPORT_TRACER_INCLUDE="${OPENSEARCH_TRANSPORT_TRACER_INCLUDE:-}"
TRANSPORT_TRACER_EXCLUDE="${OPENSEARCH_TRANSPORT_TRACER_EXCLUDE:-}"
TRANSPORT_TRACER_LOG_LEVEL="${OPENSEARCH_TRANSPORT_TRACER_LOG_LEVEL:-}"
PEERFINDER_LOG_LEVEL="${OPENSEARCH_PEERFINDER_LOG_LEVEL:-}"
HANDSHAKING_CONNECTOR_LOG_LEVEL="${OPENSEARCH_HANDSHAKING_CONNECTOR_LOG_LEVEL:-}"
COORDINATIONSTATE_LOG_LEVEL="${OPENSEARCH_COORDINATIONSTATE_LOG_LEVEL:-}"
PUBLICATION_LOG_LEVEL="${OPENSEARCH_PUBLICATION_LOG_LEVEL:-}"
CONNECTION_PROFILE_LOG_LEVEL="${OPENSEARCH_CONNECTION_PROFILE_LOG_LEVEL:-}"
CLUSTER_CONNECTION_MANAGER_LOG_LEVEL="${OPENSEARCH_CLUSTER_CONNECTION_MANAGER_LOG_LEVEL:-}"
TCP_TRANSPORT_LOG_LEVEL="${OPENSEARCH_TCP_TRANSPORT_LOG_LEVEL:-}"
NETTY4_TCP_CHANNEL_LOG_LEVEL="${OPENSEARCH_NETTY4_TCP_CHANNEL_LOG_LEVEL:-}"
NETTY4_MESSAGE_CHANNEL_HANDLER_LOG_LEVEL="${OPENSEARCH_NETTY4_MESSAGE_CHANNEL_HANDLER_LOG_LEVEL:-}"
CLASS_OVERLAY_DIR="${OPENSEARCH_CLASS_OVERLAY_DIR:-}"
CLASS_OVERLAY_FILES="${OPENSEARCH_CLASS_OVERLAY_FILES:-}"
EXTRA_JAR_OVERLAY_SPECS="${OPENSEARCH_EXTRA_JAR_OVERLAY_SPECS:-}"
FORCE_GRADLE_RUN="${OPENSEARCH_FORCE_GRADLE_RUN:-}"
find_free_port() {
  python3 - "$HOST" <<'PY'
import socket
import sys

host = sys.argv[1]
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind((host, 0))
    print(sock.getsockname()[1])
PY
}

if [[ -n "${OPENSEARCH_HTTP_PORT:-}" ]]; then
  PORT="${OPENSEARCH_HTTP_PORT}"
else
  PORT="$(find_free_port)"
fi
if [[ -n "${OPENSEARCH_TRANSPORT_PORT:-}" ]]; then
  TRANSPORT_PORT="${OPENSEARCH_TRANSPORT_PORT}"
else
  TRANSPORT_PORT="9300"
fi
WORK_DIR="${OPENSEARCH_WORK_DIR:-$(mktemp -d -t opensearch-dev.XXXXXX)}"
REPO_DIR="${OPENSEARCH_REPO_DIR:-/tmp}"
CLUSTER_NAME="${OPENSEARCH_CLUSTER_NAME:-opensearch-dev}"
NODE_NAME="${OPENSEARCH_NODE_NAME:-opensearch-dev-node}"

if [[ -n "${OPENSEARCH_URL:-}" ]]; then
  echo "Using existing OpenSearch endpoint: ${OPENSEARCH_URL}" >&2
  exit 0
fi

DEFAULT_DIST_HOME="${OPENSEARCH_ROOT}/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
OPENSEARCH_DIST_HOME="${OPENSEARCH_DIST_HOME:-${DEFAULT_DIST_HOME}}"
if [[ "${FORCE_GRADLE_RUN}" == "1" || "${FORCE_GRADLE_RUN}" == "true" ]]; then
  OPENSEARCH_BIN=""
elif [[ -x "${OPENSEARCH_DIST_HOME}/bin/opensearch" ]]; then
  OPENSEARCH_BIN="${OPENSEARCH_BIN:-${OPENSEARCH_DIST_HOME}/bin/opensearch}"
else
  OPENSEARCH_BIN="${OPENSEARCH_BIN:-${OPENSEARCH_ROOT}/distribution/src/bin/opensearch}"
fi
if [[ ! -x "${OPENSEARCH_BIN}" && ! -x "${OPENSEARCH_ROOT}/gradlew" ]]; then
  echo "OpenSearch checkout not found at ${OPENSEARCH_ROOT}; set OPENSEARCH_URL or OPENSEARCH_ROOT" >&2
  exit 2
fi

mkdir -p "${WORK_DIR}/data" "${WORK_DIR}/logs" "${REPO_DIR}"

echo "OpenSearch work dir: ${WORK_DIR}" >&2
echo "OpenSearch cluster: ${CLUSTER_NAME}" >&2
echo "OpenSearch node: ${NODE_NAME}" >&2
echo "OpenSearch URL: http://${HOST}:${PORT}" >&2
echo "OpenSearch transport: ${TRANSPORT_HOST}:${TRANSPORT_PORT}" >&2
if [[ -n "${TRANSPORT_PUBLISH_HOST}" || -n "${TRANSPORT_PUBLISH_PORT}" ]]; then
  echo "OpenSearch transport publish: ${TRANSPORT_PUBLISH_HOST:-${TRANSPORT_HOST}}:${TRANSPORT_PUBLISH_PORT:-${TRANSPORT_PORT}}" >&2
fi
if [[ -n "${PING_SCHEDULE}" ]]; then
  echo "OpenSearch transport ping_schedule: ${PING_SCHEDULE}" >&2
fi
if [[ -n "${TRANSPORT_TRACER_INCLUDE}" ]]; then
  echo "OpenSearch transport tracer include: ${TRANSPORT_TRACER_INCLUDE}" >&2
fi
if [[ -n "${TRANSPORT_TRACER_LOG_LEVEL}" ]]; then
  echo "OpenSearch transport tracer log level: ${TRANSPORT_TRACER_LOG_LEVEL}" >&2
fi
if [[ -n "${PEERFINDER_LOG_LEVEL}" ]]; then
  echo "OpenSearch PeerFinder log level: ${PEERFINDER_LOG_LEVEL}" >&2
fi
if [[ -n "${HANDSHAKING_CONNECTOR_LOG_LEVEL}" ]]; then
  echo "OpenSearch HandshakingTransportAddressConnector log level: ${HANDSHAKING_CONNECTOR_LOG_LEVEL}" >&2
fi
if [[ -n "${CONNECTION_PROFILE_LOG_LEVEL}" ]]; then
  echo "OpenSearch ConnectionProfile log level: ${CONNECTION_PROFILE_LOG_LEVEL}" >&2
fi
if [[ -n "${CLUSTER_CONNECTION_MANAGER_LOG_LEVEL}" ]]; then
  echo "OpenSearch ClusterConnectionManager log level: ${CLUSTER_CONNECTION_MANAGER_LOG_LEVEL}" >&2
fi
if [[ -n "${TCP_TRANSPORT_LOG_LEVEL}" ]]; then
  echo "OpenSearch TcpTransport log level: ${TCP_TRANSPORT_LOG_LEVEL}" >&2
fi
if [[ -n "${NETTY4_TCP_CHANNEL_LOG_LEVEL}" ]]; then
  echo "OpenSearch Netty4TcpChannel log level: ${NETTY4_TCP_CHANNEL_LOG_LEVEL}" >&2
fi
if [[ -n "${NETTY4_MESSAGE_CHANNEL_HANDLER_LOG_LEVEL}" ]]; then
  echo "OpenSearch Netty4MessageChannelHandler log level: ${NETTY4_MESSAGE_CHANNEL_HANDLER_LOG_LEVEL}" >&2
fi
if [[ -n "${FORCE_GRADLE_RUN}" ]]; then
  echo "OpenSearch force gradle run: ${FORCE_GRADLE_RUN}" >&2
fi
if [[ -n "${CLASS_OVERLAY_DIR}" ]]; then
  echo "OpenSearch class overlay dir: ${CLASS_OVERLAY_DIR}" >&2
fi
if [[ -n "${CLASS_OVERLAY_FILES}" ]]; then
  echo "OpenSearch class overlay files: ${CLASS_OVERLAY_FILES}" >&2
fi
if [[ -n "${EXTRA_JAR_OVERLAY_SPECS}" ]]; then
  echo "OpenSearch extra jar overlay specs: ${EXTRA_JAR_OVERLAY_SPECS}" >&2
fi

if [[ -x "${OPENSEARCH_BIN}" ]]; then
  if [[ -d "${OPENSEARCH_DIST_HOME}/config" && "${OPENSEARCH_BIN}" == "${OPENSEARCH_DIST_HOME}/bin/opensearch" ]]; then
    export OPENSEARCH_PATH_CONF="${OPENSEARCH_PATH_CONF:-${OPENSEARCH_DIST_HOME}/config}"
  else
    export OPENSEARCH_PATH_CONF="${OPENSEARCH_PATH_CONF:-${OPENSEARCH_ROOT}/distribution/src/config}"
  fi
  if [[ -z "${OPENSEARCH_JAVA_HOME:-}" ]] && command -v java >/dev/null 2>&1; then
    SYSTEM_JAVA_BIN="$(readlink -f "$(command -v java)")"
    export OPENSEARCH_JAVA_HOME="$(cd "$(dirname "${SYSTEM_JAVA_BIN}")/.." && pwd)"
  fi
  bin_args=(
    -Epath.data="${WORK_DIR}/data"
    -Epath.logs="${WORK_DIR}/logs"
    -Epath.repo="${REPO_DIR}"
    -Ehttp.host="${HOST}"
    -Ehttp.port="${PORT}"
    -Etransport.host="${TRANSPORT_HOST}"
    -Etransport.port="${TRANSPORT_PORT}"
    -Ecluster.name="${CLUSTER_NAME}"
    -Enode.name="${NODE_NAME}"
    -Ecluster.routing.allocation.disk.threshold_enabled=false
  )
  if [[ -n "${OPENSEARCH_DISCOVERY_SEED_HOSTS:-}" ]]; then
    bin_args+=(-Ediscovery.seed_hosts="${OPENSEARCH_DISCOVERY_SEED_HOSTS}")
  fi
  if [[ -n "${TRANSPORT_PUBLISH_HOST}" ]]; then
    bin_args+=(-Etransport.publish_host="${TRANSPORT_PUBLISH_HOST}")
  fi
  if [[ -n "${TRANSPORT_PUBLISH_PORT}" ]]; then
    bin_args+=(-Etransport.publish_port="${TRANSPORT_PUBLISH_PORT}")
  fi
  if [[ -n "${OPENSEARCH_INITIAL_CLUSTER_MANAGER_NODES:-${NODE_NAME}}" ]]; then
    bin_args+=(-Ecluster.initial_cluster_manager_nodes="${OPENSEARCH_INITIAL_CLUSTER_MANAGER_NODES:-${NODE_NAME}}")
  fi
  if [[ -n "${PING_SCHEDULE}" ]]; then
    bin_args+=(-Etransport.ping_schedule="${PING_SCHEDULE}")
  fi
  if [[ -n "${TRANSPORT_TRACER_INCLUDE}" ]]; then
    bin_args+=(-Etransport.tracer.include="${TRANSPORT_TRACER_INCLUDE}")
  fi
  if [[ -n "${TRANSPORT_TRACER_EXCLUDE}" ]]; then
    bin_args+=(-Etransport.tracer.exclude="${TRANSPORT_TRACER_EXCLUDE}")
  fi
  if [[ -n "${TRANSPORT_TRACER_LOG_LEVEL}" ]]; then
    bin_args+=(-Elogger.org.opensearch.transport.TransportService.tracer="${TRANSPORT_TRACER_LOG_LEVEL}")
  fi
  if [[ -n "${PEERFINDER_LOG_LEVEL}" ]]; then
    bin_args+=(-Elogger.org.opensearch.discovery.PeerFinder="${PEERFINDER_LOG_LEVEL}")
  fi
  if [[ -n "${HANDSHAKING_CONNECTOR_LOG_LEVEL}" ]]; then
    bin_args+=(-Elogger.org.opensearch.discovery.HandshakingTransportAddressConnector="${HANDSHAKING_CONNECTOR_LOG_LEVEL}")
  fi
  if [[ -n "${COORDINATIONSTATE_LOG_LEVEL}" ]]; then
    bin_args+=(-Elogger.org.opensearch.cluster.coordination.CoordinationState="${COORDINATIONSTATE_LOG_LEVEL}")
  fi
  if [[ -n "${PUBLICATION_LOG_LEVEL}" ]]; then
    bin_args+=(-Elogger.org.opensearch.cluster.coordination.Publication="${PUBLICATION_LOG_LEVEL}")
  fi
  if [[ -n "${CONNECTION_PROFILE_LOG_LEVEL}" ]]; then
    bin_args+=(-Elogger.org.opensearch.transport.ConnectionProfile="${CONNECTION_PROFILE_LOG_LEVEL}")
  fi
  if [[ -n "${CLUSTER_CONNECTION_MANAGER_LOG_LEVEL}" ]]; then
    bin_args+=(-Elogger.org.opensearch.transport.ClusterConnectionManager="${CLUSTER_CONNECTION_MANAGER_LOG_LEVEL}")
  fi
  if [[ -n "${TCP_TRANSPORT_LOG_LEVEL}" ]]; then
    bin_args+=(-Elogger.org.opensearch.transport.TcpTransport="${TCP_TRANSPORT_LOG_LEVEL}")
  fi
  if [[ -n "${NETTY4_TCP_CHANNEL_LOG_LEVEL}" ]]; then
    bin_args+=(-Elogger.org.opensearch.transport.netty4.Netty4TcpChannel="${NETTY4_TCP_CHANNEL_LOG_LEVEL}")
  fi
  if [[ -n "${NETTY4_MESSAGE_CHANNEL_HANDLER_LOG_LEVEL}" ]]; then
    bin_args+=(-Elogger.org.opensearch.transport.netty4.Netty4MessageChannelHandler="${NETTY4_MESSAGE_CHANNEL_HANDLER_LOG_LEVEL}")
  fi
  if [[ -n "${CLASS_OVERLAY_DIR}" && -n "${CLASS_OVERLAY_FILES}" ]]; then
    IFS=":" read -r -a overlay_files <<< "${CLASS_OVERLAY_FILES}"
    overlay_args=()
    for overlay_file in "${overlay_files[@]}"; do
      overlay_args+=("${overlay_file}")
    done
    (
      cd "${CLASS_OVERLAY_DIR}"
      jar uf "${OPENSEARCH_DIST_HOME}/lib/opensearch-3.7.0-SNAPSHOT.jar" "${overlay_args[@]}"
    )
  fi
  if [[ -n "${EXTRA_JAR_OVERLAY_SPECS}" ]]; then
    IFS=";" read -r -a overlay_specs <<< "${EXTRA_JAR_OVERLAY_SPECS}"
    for overlay_spec in "${overlay_specs[@]}"; do
      [[ -z "${overlay_spec}" ]] && continue
      IFS="|" read -r overlay_jar_path overlay_dir overlay_files <<< "${overlay_spec}"
      [[ -z "${overlay_jar_path}" || -z "${overlay_dir}" || -z "${overlay_files}" ]] && continue
      IFS=":" read -r -a overlay_file_array <<< "${overlay_files}"
      (
        cd "${overlay_dir}"
        jar uf "${overlay_jar_path}" "${overlay_file_array[@]}"
      )
    done
  fi
  exec "${OPENSEARCH_BIN}" "${bin_args[@]}"
fi

cd "${OPENSEARCH_ROOT}"
exec ./gradlew run \
  -Dtests.security.manager=false \
  -Dpath.data="${WORK_DIR}/data" \
  -Dpath.logs="${WORK_DIR}/logs" \
  -Dpath.repo="${REPO_DIR}" \
  -Dhttp.host="${HOST}" \
  -Dhttp.port="${PORT}" \
  -Dtransport.host="${TRANSPORT_HOST}" \
  -Dtransport.port="${TRANSPORT_PORT}" \
  ${TRANSPORT_PUBLISH_HOST:+-Dtransport.publish_host="${TRANSPORT_PUBLISH_HOST}"} \
  ${TRANSPORT_PUBLISH_PORT:+-Dtransport.publish_port="${TRANSPORT_PUBLISH_PORT}"} \
  -Dcluster.name="${CLUSTER_NAME}" \
  -Dnode.name="${NODE_NAME}" \
  -Ddiscovery.seed_hosts="${OPENSEARCH_DISCOVERY_SEED_HOSTS:-}" \
  -Dcluster.initial_cluster_manager_nodes="${OPENSEARCH_INITIAL_CLUSTER_MANAGER_NODES:-${NODE_NAME}}" \
  ${PING_SCHEDULE:+-Dtransport.ping_schedule="${PING_SCHEDULE}"} \
  ${TRANSPORT_TRACER_INCLUDE:+-Dtransport.tracer.include="${TRANSPORT_TRACER_INCLUDE}"} \
  ${TRANSPORT_TRACER_EXCLUDE:+-Dtransport.tracer.exclude="${TRANSPORT_TRACER_EXCLUDE}"} \
  ${TRANSPORT_TRACER_LOG_LEVEL:+-Dlogger.org.opensearch.transport.TransportService.tracer="${TRANSPORT_TRACER_LOG_LEVEL}"} \
  ${PEERFINDER_LOG_LEVEL:+-Dlogger.org.opensearch.discovery.PeerFinder="${PEERFINDER_LOG_LEVEL}"} \
  ${HANDSHAKING_CONNECTOR_LOG_LEVEL:+-Dlogger.org.opensearch.discovery.HandshakingTransportAddressConnector="${HANDSHAKING_CONNECTOR_LOG_LEVEL}"} \
  ${COORDINATIONSTATE_LOG_LEVEL:+-Dlogger.org.opensearch.cluster.coordination.CoordinationState="${COORDINATIONSTATE_LOG_LEVEL}"} \
  ${PUBLICATION_LOG_LEVEL:+-Dlogger.org.opensearch.cluster.coordination.Publication="${PUBLICATION_LOG_LEVEL}"} \
  ${CONNECTION_PROFILE_LOG_LEVEL:+-Dlogger.org.opensearch.transport.ConnectionProfile="${CONNECTION_PROFILE_LOG_LEVEL}"} \
  ${CLUSTER_CONNECTION_MANAGER_LOG_LEVEL:+-Dlogger.org.opensearch.transport.ClusterConnectionManager="${CLUSTER_CONNECTION_MANAGER_LOG_LEVEL}"} \
  ${TCP_TRANSPORT_LOG_LEVEL:+-Dlogger.org.opensearch.transport.TcpTransport="${TCP_TRANSPORT_LOG_LEVEL}"} \
  -Dopensearch.plugins.security.disabled=true
