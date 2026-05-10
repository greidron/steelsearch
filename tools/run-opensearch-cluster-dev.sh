#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${OPENSEARCH_CLUSTER_NAME:-opensearch-dev}"
NODE_COUNT="${OPENSEARCH_NODE_COUNT:-3}"
WORK_DIR="${OPENSEARCH_CLUSTER_WORK_DIR:-$(mktemp -d -t opensearch-cluster-dev.XXXXXX)}"
HOST="${OPENSEARCH_HTTP_HOST:-127.0.0.1}"
IMAGE="${OPENSEARCH_VECTOR_DOCKER_IMAGE:-opensearchproject/opensearch:2.19.0}"
CONTAINER_PREFIX="${OPENSEARCH_CLUSTER_CONTAINER_PREFIX:-steelsearch-bench-opensearch}"
NETWORK_NAME="${OPENSEARCH_CLUSTER_NETWORK_NAME:-${CONTAINER_PREFIX}-net}"
MANIFEST="${WORK_DIR}/cluster.json"
CONTAINERS=()

find_free_port() {
  python3 - "$1" <<'PY'
import socket
import sys

host = sys.argv[1]
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind((host, 0))
    print(sock.getsockname()[1])
PY
}

cleanup() {
  for container in "${CONTAINERS[@]:-}"; do
    docker rm -f "${container}" >/dev/null 2>&1 || true
  done
  docker network rm "${NETWORK_NAME}" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

http_ports=()
transport_ports=()
node_names=()
for ((i = 0; i < NODE_COUNT; i++)); do
  if [[ -n "${OPENSEARCH_BASE_HTTP_PORT:-}" ]]; then
    http_ports+=("$((OPENSEARCH_BASE_HTTP_PORT + i))")
  else
    http_ports+=("$(find_free_port "${HOST}")")
  fi

  if [[ -n "${OPENSEARCH_BASE_TRANSPORT_PORT:-}" ]]; then
    transport_ports+=("$((OPENSEARCH_BASE_TRANSPORT_PORT + i))")
  else
    transport_ports+=("$(find_free_port "${HOST}")")
  fi

  node_names+=("opensearch-node-$((i + 1))")
done

seed_csv="$(IFS=,; echo "${node_names[*]}")"
initial_cluster_manager_nodes="${seed_csv}"

mkdir -p "${WORK_DIR}"
python3 - "${MANIFEST}" "${CLUSTER_NAME}" "${WORK_DIR}" "${HOST}" "${seed_csv}" "${http_ports[*]}" "${transport_ports[*]}" <<'PY'
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
cluster_name = sys.argv[2]
work_dir = Path(sys.argv[3])
host = sys.argv[4]
node_names = [name for name in sys.argv[5].split(",") if name]
http_ports = [int(port) for port in sys.argv[6].split()]
transport_ports = [int(port) for port in sys.argv[7].split()]

nodes = []
for index, (node_name, http_port, transport_port) in enumerate(zip(node_names, http_ports, transport_ports), start=1):
    nodes.append(
        {
            "node_name": node_name,
            "http_url": f"http://{host}:{http_port}",
            "http_host": host,
            "http_port": http_port,
            "transport_address": f"{host}:{transport_port}",
            "transport_port": transport_port,
            "container_name": f"{node_name}",
        }
    )

manifest = {
    "cluster_name": cluster_name,
    "work_dir": str(work_dir),
    "nodes": nodes,
    "initial_cluster_manager_nodes": node_names,
}
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY

echo "OpenSearch Docker cluster work dir: ${WORK_DIR}" >&2
echo "OpenSearch Docker cluster manifest: ${MANIFEST}" >&2
echo "OpenSearch Docker image: ${IMAGE}" >&2

docker network rm "${NETWORK_NAME}" >/dev/null 2>&1 || true
docker network create "${NETWORK_NAME}" >/dev/null

for ((i = 0; i < NODE_COUNT; i++)); do
  node_number=$((i + 1))
  node_name="${node_names[$i]}"
  container_name="${CONTAINER_PREFIX}-${node_number}"
  CONTAINERS+=("${container_name}")
  echo "starting ${container_name}: http ${HOST}:${http_ports[$i]} transport ${HOST}:${transport_ports[$i]}" >&2
  if [[ "${OPENSEARCH_CLUSTER_DRY_RUN:-0}" == "1" ]]; then
    continue
  fi

  docker rm -f "${container_name}" >/dev/null 2>&1 || true
  docker run -d \
    --name "${container_name}" \
    --network "${NETWORK_NAME}" \
    --network-alias "${node_name}" \
    -p "${HOST}:${http_ports[$i]}:9200" \
    -p "${HOST}:${transport_ports[$i]}:9300" \
    -e cluster.name="${CLUSTER_NAME}" \
    -e node.name="${node_name}" \
    -e discovery.seed_hosts="${seed_csv}" \
    -e cluster.initial_cluster_manager_nodes="${initial_cluster_manager_nodes}" \
    -e DISABLE_SECURITY_PLUGIN=true \
    -e DISABLE_INSTALL_DEMO_CONFIG=true \
    -e OPENSEARCH_JAVA_OPTS="${OPENSEARCH_JAVA_OPTS:--Xms512m -Xmx512m}" \
    "${IMAGE}" >/dev/null
done

if [[ "${OPENSEARCH_CLUSTER_DRY_RUN:-0}" == "1" ]]; then
  echo "Dry run complete; no Docker containers were started." >&2
  exit 0
fi

echo "Waiting for OpenSearch Docker cluster health..." >&2
for ((i = 0; i < NODE_COUNT; i++)); do
  http_port="${http_ports[$i]}"
  ready=0
  for _ in {1..180}; do
    if curl -fsS "http://${HOST}:${http_port}/_cluster/health?wait_for_nodes=>=${NODE_COUNT}&timeout=1s" >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 1
  done
  if [[ "${ready}" != "1" ]]; then
    echo "OpenSearch node ${node_names[$i]} did not become ready" >&2
    docker logs "${CONTAINERS[$i]}" >&2 || true
    exit 1
  fi
  curl -fsS "http://${HOST}:${http_port}/_cluster/health?pretty"
  echo
done

echo "Docker cluster is running. Press Ctrl-C to stop all nodes." >&2
while true; do
  sleep 3600
done
