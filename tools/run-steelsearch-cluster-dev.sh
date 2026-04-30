#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER_NAME="${STEELSEARCH_CLUSTER_NAME:-steelsearch-dev}"
NODE_COUNT="${STEELSEARCH_NODE_COUNT:-3}"
WORK_DIR="${STEELSEARCH_CLUSTER_WORK_DIR:-$(mktemp -d -t steelsearch-cluster-dev.XXXXXX)}"
HTTP_HOST="${STEELSEARCH_HTTP_HOST:-0.0.0.0}"
TRANSPORT_HOST="${STEELSEARCH_TRANSPORT_HOST:-0.0.0.0}"
HTTP_ACCESS_HOST="${STEELSEARCH_HTTP_ACCESS_HOST:-127.0.0.1}"
TRANSPORT_ACCESS_HOST="${STEELSEARCH_TRANSPORT_ACCESS_HOST:-127.0.0.1}"
MANIFEST="${WORK_DIR}/cluster.json"
PIDS=()

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
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT INT TERM

http_ports=()
transport_ports=()

for ((i = 0; i < NODE_COUNT; i++)); do
  if [[ -n "${STEELSEARCH_BASE_HTTP_PORT:-}" ]]; then
    http_ports+=("$((STEELSEARCH_BASE_HTTP_PORT + i))")
  else
    http_ports+=("$(find_free_port "${HTTP_HOST}")")
  fi

  if [[ -n "${STEELSEARCH_BASE_TRANSPORT_PORT:-}" ]]; then
    transport_ports+=("$((STEELSEARCH_BASE_TRANSPORT_PORT + i))")
  else
    transport_ports+=("$(find_free_port "${TRANSPORT_HOST}")")
  fi
done

seed_hosts=()
for ((i = 0; i < NODE_COUNT; i++)); do
  seed_hosts+=("${TRANSPORT_ACCESS_HOST}:${transport_ports[$i]}")
done
seed_csv="$(IFS=,; echo "${seed_hosts[*]}")"

mkdir -p "${WORK_DIR}"
python3 - "${MANIFEST}" "${CLUSTER_NAME}" "${HTTP_ACCESS_HOST}" "${TRANSPORT_ACCESS_HOST}" "${WORK_DIR}" "${seed_csv}" "${http_ports[*]}" "${transport_ports[*]}" <<'PY'
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
cluster_name = sys.argv[2]
http_host = sys.argv[3]
transport_host = sys.argv[4]
work_dir = Path(sys.argv[5])
seed_hosts = [host for host in sys.argv[6].split(",") if host]
http_ports = [int(port) for port in sys.argv[7].split()]
transport_ports = [int(port) for port in sys.argv[8].split()]

nodes = []
for index, (http_port, transport_port) in enumerate(zip(http_ports, transport_ports), start=1):
    node_dir = work_dir / f"node-{index}"
    nodes.append(
        {
            "node_id": f"steel-node-{index}",
            "node_name": f"steel-node-{index}",
            "http_url": f"http://{http_host}:{http_port}",
            "http_host": http_host,
            "http_port": http_port,
            "transport_host": transport_host,
            "transport_port": transport_port,
            "transport_address": f"{transport_host}:{transport_port}",
            "data_path": str(node_dir / "data"),
            "log_path": str(node_dir / "logs"),
        }
    )

manifest = {
    "cluster_name": cluster_name,
    "work_dir": str(work_dir),
    "seed_hosts": seed_hosts,
    "nodes": nodes,
}
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY

echo "Steelsearch cluster work dir: ${WORK_DIR}" >&2
echo "Steelsearch cluster manifest: ${MANIFEST}" >&2
echo "Steelsearch seed hosts: ${seed_csv}" >&2

for ((i = 0; i < NODE_COUNT; i++)); do
  node_number=$((i + 1))
  http_port="${http_ports[$i]}"
  transport_port="${transport_ports[$i]}"
  node_dir="${WORK_DIR}/node-${node_number}"
  mkdir -p "${node_dir}/data" "${node_dir}/logs"

  echo "starting steel-node-${node_number}: bind http://${HTTP_HOST}:${http_port} access http://${HTTP_ACCESS_HOST}:${http_port} bind transport ${TRANSPORT_HOST}:${transport_port} access transport ${TRANSPORT_ACCESS_HOST}:${transport_port}" >&2
  if [[ "${STEELSEARCH_CLUSTER_DRY_RUN:-0}" == "1" ]]; then
    continue
  fi

  (
    cd "${ROOT}"
    exec cargo run -p os-node --features standalone-runtime --bin steelsearch --manifest-path "${ROOT}/Cargo.toml" -- \
      --http.host "${HTTP_HOST}" \
      --http.port "${http_port}" \
      --transport.host "${TRANSPORT_HOST}" \
      --transport.port "${transport_port}" \
      --node.id "steel-node-${node_number}" \
      --node.name "steel-node-${node_number}" \
      --node.roles "cluster_manager,data,ingest" \
      --cluster.name "${CLUSTER_NAME}" \
      --discovery.seed_hosts "${seed_csv}" \
      --path.data "${node_dir}/data" \
      >"${node_dir}/logs/stdout.log" \
      2>"${node_dir}/logs/stderr.log"
  ) &
  PIDS+=("$!")
done

if [[ "${STEELSEARCH_CLUSTER_DRY_RUN:-0}" == "1" ]]; then
  echo "Dry run complete; no daemon processes were started." >&2
  exit 0
fi

echo "Waiting for nodes to expose development cluster views..." >&2
for ((i = 0; i < NODE_COUNT; i++)); do
  http_port="${http_ports[$i]}"
  ready=0
  for _ in {1..80}; do
    if curl -fsS "http://${HTTP_ACCESS_HOST}:${http_port}/_steelsearch/dev/cluster" >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 0.25
  done
  if [[ "${ready}" != "1" ]]; then
    echo "steel-node-$((i + 1)) did not become ready; stderr follows:" >&2
    tail -80 "${WORK_DIR}/node-$((i + 1))/logs/stderr.log" >&2 || true
    exit 1
  fi
  curl -fsS "http://${HTTP_ACCESS_HOST}:${http_port}/_steelsearch/dev/cluster"
  echo
done

echo "Cluster is running. Press Ctrl-C to stop all nodes." >&2
wait
