#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${JAVA_RUST_MIXED_MEMBERSHIP_WORK_DIR:-$(mktemp -d -t java-rust-mixed-membership.XXXXXX)}"
REPORT_PATH="${WORK_DIR}/report.json"
OPENSEARCH_WORK_DIR="${WORK_DIR}/opensearch"
STEELSEARCH_WORK_DIR="${WORK_DIR}/steelsearch"
TRANSPORT_IDENTITY_WORK_DIR="${WORK_DIR}/transport-identity"
mkdir -p "${OPENSEARCH_WORK_DIR}" "${STEELSEARCH_WORK_DIR}"
OPENSEARCH_STARTUP_TIMEOUT_SECONDS="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_STARTUP_TIMEOUT_SECONDS:-120}"
MEMBERSHIP_TIMEOUT_SECONDS="${JAVA_RUST_MIXED_MEMBERSHIP_MEMBERSHIP_TIMEOUT_SECONDS:-180}"
LIVE_HANDOFF_REPORT_PATH="${JAVA_RUST_MIXED_MEMBERSHIP_LIVE_HANDOFF_REPORT_PATH:-}"
FORMED_HANDOFF_REPORT_PATH="${JAVA_RUST_MIXED_MEMBERSHIP_FORMED_HANDOFF_REPORT_PATH:-}"
KEEP_ALIVE_SECONDS="${JAVA_RUST_MIXED_MEMBERSHIP_KEEP_ALIVE_SECONDS:-0}"
OPENSEARCH_PING_SCHEDULE="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_PING_SCHEDULE:-}"
OPENSEARCH_PEERFINDER_LOG_LEVEL="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_PEERFINDER_LOG_LEVEL:-}"
OPENSEARCH_HANDSHAKING_CONNECTOR_LOG_LEVEL="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_HANDSHAKING_CONNECTOR_LOG_LEVEL:-}"
OPENSEARCH_COORDINATIONSTATE_LOG_LEVEL="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_COORDINATIONSTATE_LOG_LEVEL:-}"
OPENSEARCH_PUBLICATION_LOG_LEVEL="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_PUBLICATION_LOG_LEVEL:-}"
OPENSEARCH_CONNECTION_PROFILE_LOG_LEVEL="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_CONNECTION_PROFILE_LOG_LEVEL:-}"
OPENSEARCH_CLUSTER_CONNECTION_MANAGER_LOG_LEVEL="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_CLUSTER_CONNECTION_MANAGER_LOG_LEVEL:-}"
OPENSEARCH_TCP_TRANSPORT_LOG_LEVEL="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_TCP_TRANSPORT_LOG_LEVEL:-}"
OPENSEARCH_NETTY4_TCP_CHANNEL_LOG_LEVEL="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_NETTY4_TCP_CHANNEL_LOG_LEVEL:-}"
OPENSEARCH_NETTY4_MESSAGE_CHANNEL_HANDLER_LOG_LEVEL="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_NETTY4_MESSAGE_CHANNEL_HANDLER_LOG_LEVEL:-}"
OPENSEARCH_CLASS_OVERLAY_DIR="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_CLASS_OVERLAY_DIR:-}"
OPENSEARCH_CLASS_OVERLAY_FILES="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_CLASS_OVERLAY_FILES:-}"
OPENSEARCH_EXTRA_JAR_OVERLAY_SPECS="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_EXTRA_JAR_OVERLAY_SPECS:-}"
OPENSEARCH_FORCE_GRADLE_RUN="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_FORCE_GRADLE_RUN:-}"
OPENSEARCH_FORCE_LOW_LEVEL_HANDSHAKE_SUCCESS_ON_TIMEOUT="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_FORCE_LOW_LEVEL_HANDSHAKE_SUCCESS_ON_TIMEOUT:-}"
OPENSEARCH_FORCE_EXECUTE_HANDSHAKE_LISTENER_SUCCESS_ON_FAILURE="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_FORCE_EXECUTE_HANDSHAKE_LISTENER_SUCCESS_ON_FAILURE:-}"
OPENSEARCH_FORCE_LOW_LEVEL_HANDSHAKE_SUCCESS_IMMEDIATELY_AFTER_SEND="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_FORCE_LOW_LEVEL_HANDSHAKE_SUCCESS_IMMEDIATELY_AFTER_SEND:-}"
USE_ASYMMETRIC_SEEDS="${JAVA_RUST_MIXED_MEMBERSHIP_USE_ASYMMETRIC_SEEDS:-0}"
SKIP_SEED_PEER_IDENTITY_MANIFEST="${JAVA_RUST_MIXED_MEMBERSHIP_SKIP_SEED_PEER_IDENTITY_MANIFEST:-0}"

find_free_port() {
  python3 - <<'PY'
import socket
with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    print(s.getsockname()[1])
PY
}

cleanup() {
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT

if [[ -n "${LIVE_HANDOFF_REPORT_PATH}" ]]; then
  rm -f "${LIVE_HANDOFF_REPORT_PATH}"
fi
if [[ -n "${FORMED_HANDOFF_REPORT_PATH}" ]]; then
  rm -f "${FORMED_HANDOFF_REPORT_PATH}"
fi

write_env_snapshot() {
  local output_path="$1"
  shift
  python3 - "$output_path" "$@" <<'PY'
import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
data = {}
for item in sys.argv[2:]:
    key, value = item.split("=", 1)
    data[key] = value
output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
}

write_report() {
  local output_path="${4:-$REPORT_PATH}"
  python3 - "$output_path" "$WORK_DIR" "$INITIAL_CLUSTER_MANAGER_NODES" "$SUCCESS_HARNESS_CLUSTER_URL" "$JAVA_NODE_NAME" "$RUST_NODE_NAME" "$1" "$2" "$3" <<'PY'
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
work_dir = Path(sys.argv[2])
initial_cluster_manager_nodes = [item for item in sys.argv[3].split(",") if item]
success_harness_cluster_url = sys.argv[4]
java_node_name = sys.argv[5]
rust_node_name = sys.argv[6]
node_count = int(sys.argv[7])
membership_formed = sys.argv[8] == "true"
failure_stage = sys.argv[9]

steel_stdout_path = work_dir / "steelsearch" / "stdout.log"
steel_stderr_path = work_dir / "steelsearch" / "stderr.log"
transport_identity_report_path = work_dir / "transport-identity" / "transport-handshake-report.json"
transport_identity_parsed_path = work_dir / "transport-identity" / "transport-handshake-response-parsed.json"
gateway_state_path = work_dir / "steelsearch" / "data" / "gateway-state.json"
membership_state_path = work_dir / "steelsearch" / "data" / "production-membership.json"
transport_capture_path = work_dir / "steelsearch" / "data" / "transport-seed-capture.json"
steelsearch_transport_probe_path = work_dir / "steelsearch" / "transport-connect.json"
steelsearch_transport_handshake_probe_path = work_dir / "steelsearch" / "transport-handshake.json"
opensearch_pid_path = work_dir / "opensearch" / "pid"
steelsearch_pid_path = work_dir / "steelsearch" / "pid"
opensearch_start_cmd_path = work_dir / "opensearch" / "start-command.txt"
steelsearch_start_cmd_path = work_dir / "steelsearch" / "start-command.txt"
opensearch_launch_env_path = work_dir / "opensearch" / "launch-env.json"
steelsearch_launch_env_path = work_dir / "steelsearch" / "launch-env.json"
steel_stdout = steel_stdout_path.read_text(encoding="utf-8", errors="replace") if steel_stdout_path.exists() else ""
steel_stderr = steel_stderr_path.read_text(encoding="utf-8", errors="replace") if steel_stderr_path.exists() else ""
seed_peer_identity = None
if transport_identity_parsed_path.exists():
    seed_peer_identity = json.loads(transport_identity_parsed_path.read_text(encoding="utf-8"))
gateway_state = None
bootstrap_remote_nodes = []
if gateway_state_path.exists():
    gateway_state = json.loads(gateway_state_path.read_text(encoding="utf-8"))
    bootstrap_remote_nodes = [
        {
            "node_id": node.get("node_id"),
            "node_name": node.get("node_name"),
            "transport_address": node.get("transport_address"),
            "roles": node.get("roles", []),
        }
        for node in gateway_state.get("cluster_state", {}).get("nodes", [])
        if not node.get("local", False)
    ]
membership_state = None
membership_members = []
if membership_state_path.exists():
    membership_state = json.loads(membership_state_path.read_text(encoding="utf-8"))
    membership_members = [
        {
            "node_id": node_id,
            "node_name": node.get("node_name"),
            "roles": node.get("roles", []),
            "cluster_uuid": node.get("cluster_uuid"),
        }
        for node_id, node in membership_state.get("members", {}).items()
    ]
steelsearch_transport_probe = None
if steelsearch_transport_probe_path.exists():
    steelsearch_transport_probe = json.loads(steelsearch_transport_probe_path.read_text(encoding="utf-8"))
steelsearch_transport_handshake_probe = None
if steelsearch_transport_handshake_probe_path.exists():
    steelsearch_transport_handshake_probe = json.loads(
        steelsearch_transport_handshake_probe_path.read_text(encoding="utf-8")
    )
steelsearch_transport_capture = None
if transport_capture_path.exists():
    steelsearch_transport_capture = json.loads(transport_capture_path.read_text(encoding="utf-8"))

blocker_class = None
if not membership_formed:
    if failure_stage == "opensearch_startup_timeout":
        blocker_class = "opensearch_startup_timeout"
    elif "mixed Java same-cluster participation is not implemented" in steel_stderr:
        blocker_class = "same_cluster_participation_unimplemented"
    elif "production mode is blocked until" in steel_stderr:
        blocker_class = "production_mode_blocked"
    elif "standalone HTTP compatibility surface only" in steel_stdout or "standalone HTTP compatibility surface only" in steel_stderr:
        blocker_class = "standalone_only_bootstrap"
    elif failure_stage == "membership_timeout":
        blocker_class = "membership_timeout"
    else:
        blocker_class = "membership_not_formed"

report = {
    "work_dir": str(work_dir),
    "initial_cluster_manager_nodes": initial_cluster_manager_nodes,
    "success_harness_handoff": {
        "cluster_url": success_harness_cluster_url,
        "java_node": java_node_name,
        "rust_node": rust_node_name,
    },
    "observed_node_count": node_count,
    "membership_formed": membership_formed,
    "failure_stage": failure_stage,
    "blocker_class": blocker_class,
    "artifacts": {
        "opensearch_stderr": str(work_dir / "opensearch" / "stderr.log"),
        "opensearch_stdout": str(work_dir / "opensearch" / "stdout.log"),
        "opensearch_pid": str(opensearch_pid_path),
        "opensearch_start_command": str(opensearch_start_cmd_path),
        "opensearch_launch_env": str(opensearch_launch_env_path),
        "steelsearch_stderr": str(work_dir / "steelsearch" / "stderr.log"),
        "steelsearch_stdout": str(work_dir / "steelsearch" / "stdout.log"),
        "steelsearch_pid": str(steelsearch_pid_path),
        "steelsearch_start_command": str(steelsearch_start_cmd_path),
        "steelsearch_launch_env": str(steelsearch_launch_env_path),
        "transport_handshake_report": str(transport_identity_report_path),
        "transport_handshake_parsed": str(transport_identity_parsed_path),
        "steelsearch_gateway_state": str(gateway_state_path),
        "steelsearch_membership_state": str(membership_state_path),
        "steelsearch_transport_capture": str(transport_capture_path),
        "steelsearch_transport_probe": str(steelsearch_transport_probe_path),
        "steelsearch_transport_handshake_probe": str(steelsearch_transport_handshake_probe_path),
    },
    "seed_peer_identity": seed_peer_identity,
    "steelsearch_bootstrap_remote_nodes": bootstrap_remote_nodes,
    "steelsearch_membership_members": membership_members,
    "steelsearch_transport_capture": steelsearch_transport_capture,
    "steelsearch_transport_probe": steelsearch_transport_probe,
    "steelsearch_transport_handshake_probe": steelsearch_transport_handshake_probe,
    "markers": {
        "steelsearch_standalone_only": (
            "standalone HTTP compatibility surface only" in steel_stdout
            or "standalone HTTP compatibility surface only" in steel_stderr
        ),
        "steelsearch_production_mode_blocked": (
            "production mode is blocked until" in steel_stderr
        ),
        "steelsearch_same_cluster_participation_unimplemented": (
            "mixed Java same-cluster participation is not implemented" in steel_stderr
        ),
        "steelsearch_native_transport_join_participation": (
            "mixed Java native transport join participation active" in steel_stderr
        ),
        "steelsearch_bootstrap_uses_seed_peer_identity": bool(
            seed_peer_identity
            and bootstrap_remote_nodes
            and any(
                node.get("node_id") == seed_peer_identity.get("discovery_node", {}).get("id")
                and node.get("transport_address") == seed_peer_identity.get("discovery_node", {}).get("transport_address")
                for node in bootstrap_remote_nodes
            )
        ),
        "steelsearch_membership_state_persisted": membership_state is not None,
        "steelsearch_transport_accepting_connections": bool(
            steelsearch_transport_probe and steelsearch_transport_probe.get("tcp_connected") is True
        ),
        "steelsearch_transport_handshake_accepted": bool(
            steelsearch_transport_handshake_probe
            and steelsearch_transport_handshake_probe.get("response_received") is True
            and steelsearch_transport_handshake_probe.get("response_starts_with_es") is True
        ),
        "steelsearch_transport_follow_up_observed": bool(
            steelsearch_transport_capture
            and any(capture.get("follow_up_frame") for capture in steelsearch_transport_capture)
        ),
    },
}
report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
PY
}

wait_for_http() {
  local url="$1"
  local timeout_seconds="$2"
  local started_at
  started_at="$(date +%s)"
  while true; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    if (( $(date +%s) - started_at >= timeout_seconds )); then
      return 1
    fi
    sleep 1
  done
}

collect_seed_peer_identity() {
  mkdir -p "${TRANSPORT_IDENTITY_WORK_DIR}"
  local frame_hex
  frame_hex="$(bash "${ROOT_DIR}/tools/dump_java_transport_handshake_frame.sh")"
  python3 "${ROOT_DIR}/tools/send_opensearch_tcp_handshake_probe.py" \
    --host 127.0.0.1 \
    --port "${OS_TRANSPORT}" \
    --action internal:transport/handshake \
    --frame-hex "${frame_hex}" \
    --timeout-seconds 2.0 \
    --report-path "${TRANSPORT_IDENTITY_WORK_DIR}/transport-handshake-report.json" \
    >/dev/null
  local response_hex
  response_hex="$(
    python3 - "${TRANSPORT_IDENTITY_WORK_DIR}/transport-handshake-report.json" <<'PY'
import json
import sys
from pathlib import Path
report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(report.get("response_hex", ""))
PY
  )"
  if [[ -n "${response_hex}" ]]; then
    bash "${ROOT_DIR}/tools/parse_java_transport_handshake_response.sh" \
      --response-hex "${response_hex}" \
      --report-path "${TRANSPORT_IDENTITY_WORK_DIR}/transport-handshake-response-parsed.json" \
      >/dev/null
  fi
}

probe_steelsearch_transport() {
  python3 - "${SS_TRANSPORT}" "${STEELSEARCH_WORK_DIR}/transport-connect.json" <<'PY'
import json
import socket
import sys
from pathlib import Path

port = int(sys.argv[1])
path = Path(sys.argv[2])
report = {
    "host": "127.0.0.1",
    "port": port,
    "tcp_connected": False,
    "error": None,
}
try:
    with socket.create_connection(("127.0.0.1", port), timeout=1.5):
        report["tcp_connected"] = True
except Exception as exc:
    report["error"] = f"{type(exc).__name__}: {exc}"
path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report))
PY
}

probe_steelsearch_transport_handshake() {
  local frame_hex
  frame_hex="$(bash "${ROOT_DIR}/tools/dump_java_tcp_handshake_frame.sh")"
  python3 "${ROOT_DIR}/tools/send_opensearch_tcp_handshake_probe.py" \
    --host 127.0.0.1 \
    --port "${SS_TRANSPORT}" \
    --action internal:tcp/handshake \
    --frame-hex "${frame_hex}" \
    --timeout-seconds 2.0 \
    --report-path "${STEELSEARCH_WORK_DIR}/transport-handshake.json" \
    >/dev/null
}

current_node_count() {
  curl -fsS "http://127.0.0.1:${OS_HTTP}/_cat/nodes?format=json" \
    | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))'
}

OS_HTTP="${JAVA_RUST_MIXED_MEMBERSHIP_OS_HTTP_PORT:-$(find_free_port)}"
OS_TRANSPORT="${JAVA_RUST_MIXED_MEMBERSHIP_OS_TRANSPORT_PORT:-$(find_free_port)}"
SS_HTTP="${JAVA_RUST_MIXED_MEMBERSHIP_SS_HTTP_PORT:-$(find_free_port)}"
SS_TRANSPORT="${JAVA_RUST_MIXED_MEMBERSHIP_SS_TRANSPORT_PORT:-$(find_free_port)}"
SUCCESS_HARNESS_CLUSTER_URL="http://127.0.0.1:${OS_HTTP}"
CLUSTER_NAME="${JAVA_RUST_MIXED_MEMBERSHIP_CLUSTER_NAME:-mixed-java-rust-dev}"
JAVA_NODE_NAME="${JAVA_RUST_MIXED_MEMBERSHIP_JAVA_NODE_NAME:-java-primary-1}"
RUST_NODE_NAME="${JAVA_RUST_MIXED_MEMBERSHIP_RUST_NODE_NAME:-rust-replica-1}"
if [[ -n "${JAVA_RUST_MIXED_MEMBERSHIP_INITIAL_CLUSTER_MANAGER_NODES:-}" ]]; then
  INITIAL_CLUSTER_MANAGER_NODES="${JAVA_RUST_MIXED_MEMBERSHIP_INITIAL_CLUSTER_MANAGER_NODES}"
elif [[ -n "${JAVA_RUST_MIXED_MEMBERSHIP_JAVA_WRITE_FORWARDING_VALIDATED:-}" ]]; then
  INITIAL_CLUSTER_MANAGER_NODES="${JAVA_NODE_NAME},${RUST_NODE_NAME}"
else
  INITIAL_CLUSTER_MANAGER_NODES="${JAVA_NODE_NAME}"
fi
DEFAULT_SEEDS="127.0.0.1:${OS_TRANSPORT},127.0.0.1:${SS_TRANSPORT}"
if [[ "${USE_ASYMMETRIC_SEEDS}" == "1" ]]; then
  OPENSEARCH_SEEDS="127.0.0.1:${OS_TRANSPORT}"
  STEELSEARCH_SEEDS="127.0.0.1:${OS_TRANSPORT}"
else
  OPENSEARCH_SEEDS="${DEFAULT_SEEDS}"
  STEELSEARCH_SEEDS="${DEFAULT_SEEDS}"
fi

opensearch_env=(
  OPENSEARCH_HTTP_HOST=127.0.0.1
  OPENSEARCH_TRANSPORT_HOST=127.0.0.1
  OPENSEARCH_HTTP_PORT="${OS_HTTP}"
  OPENSEARCH_TRANSPORT_PORT="${OS_TRANSPORT}"
  OPENSEARCH_CLUSTER_NAME="${CLUSTER_NAME}"
  OPENSEARCH_NODE_NAME="${JAVA_NODE_NAME}"
  OPENSEARCH_DISCOVERY_SEED_HOSTS="${OPENSEARCH_SEEDS}"
  OPENSEARCH_INITIAL_CLUSTER_MANAGER_NODES="${INITIAL_CLUSTER_MANAGER_NODES}"
  OPENSEARCH_PING_SCHEDULE="${OPENSEARCH_PING_SCHEDULE}"
  OPENSEARCH_PEERFINDER_LOG_LEVEL="${OPENSEARCH_PEERFINDER_LOG_LEVEL}"
  OPENSEARCH_HANDSHAKING_CONNECTOR_LOG_LEVEL="${OPENSEARCH_HANDSHAKING_CONNECTOR_LOG_LEVEL}"
  OPENSEARCH_COORDINATIONSTATE_LOG_LEVEL="${OPENSEARCH_COORDINATIONSTATE_LOG_LEVEL}"
  OPENSEARCH_PUBLICATION_LOG_LEVEL="${OPENSEARCH_PUBLICATION_LOG_LEVEL}"
  OPENSEARCH_CONNECTION_PROFILE_LOG_LEVEL="${OPENSEARCH_CONNECTION_PROFILE_LOG_LEVEL}"
  OPENSEARCH_CLUSTER_CONNECTION_MANAGER_LOG_LEVEL="${OPENSEARCH_CLUSTER_CONNECTION_MANAGER_LOG_LEVEL}"
  OPENSEARCH_TCP_TRANSPORT_LOG_LEVEL="${OPENSEARCH_TCP_TRANSPORT_LOG_LEVEL}"
  OPENSEARCH_NETTY4_TCP_CHANNEL_LOG_LEVEL="${OPENSEARCH_NETTY4_TCP_CHANNEL_LOG_LEVEL}"
  OPENSEARCH_NETTY4_MESSAGE_CHANNEL_HANDLER_LOG_LEVEL="${OPENSEARCH_NETTY4_MESSAGE_CHANNEL_HANDLER_LOG_LEVEL}"
  OPENSEARCH_CLASS_OVERLAY_DIR="${OPENSEARCH_CLASS_OVERLAY_DIR}"
  OPENSEARCH_CLASS_OVERLAY_FILES="${OPENSEARCH_CLASS_OVERLAY_FILES}"
  OPENSEARCH_EXTRA_JAR_OVERLAY_SPECS="${OPENSEARCH_EXTRA_JAR_OVERLAY_SPECS}"
  OPENSEARCH_FORCE_GRADLE_RUN="${OPENSEARCH_FORCE_GRADLE_RUN}"
  STEELSEARCH_FORCE_LOW_LEVEL_HANDSHAKE_SUCCESS_ON_TIMEOUT="${OPENSEARCH_FORCE_LOW_LEVEL_HANDSHAKE_SUCCESS_ON_TIMEOUT}"
  STEELSEARCH_FORCE_EXECUTE_HANDSHAKE_LISTENER_SUCCESS_ON_FAILURE="${OPENSEARCH_FORCE_EXECUTE_HANDSHAKE_LISTENER_SUCCESS_ON_FAILURE}"
  STEELSEARCH_FORCE_LOW_LEVEL_HANDSHAKE_SUCCESS_IMMEDIATELY_AFTER_SEND="${OPENSEARCH_FORCE_LOW_LEVEL_HANDSHAKE_SUCCESS_IMMEDIATELY_AFTER_SEND}"
  OPENSEARCH_WORK_DIR="${OPENSEARCH_WORK_DIR}"
)
if [[ -n "${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_JAVA_OPTS:-}" ]]; then
  opensearch_env+=(OPENSEARCH_JAVA_OPTS="${JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_JAVA_OPTS}")
fi
write_env_snapshot "${OPENSEARCH_WORK_DIR}/launch-env.json" "${opensearch_env[@]}"

env "${opensearch_env[@]}" bash "${ROOT_DIR}/tools/run-opensearch-dev.sh" \
  >"${OPENSEARCH_WORK_DIR}/stdout.log" \
  2>"${OPENSEARCH_WORK_DIR}/stderr.log" &
echo "$!" >"${OPENSEARCH_WORK_DIR}/pid"
printf '%s\n' "OPENSEARCH_HTTP_PORT=${OS_HTTP} OPENSEARCH_TRANSPORT_PORT=${OS_TRANSPORT} OPENSEARCH_NODE_NAME=${JAVA_NODE_NAME} OPENSEARCH_CLUSTER_NAME=${CLUSTER_NAME} bash ${ROOT_DIR}/tools/run-opensearch-dev.sh" >"${OPENSEARCH_WORK_DIR}/start-command.txt"

for _ in $(seq 1 120); do
  :
done
if ! wait_for_http "http://127.0.0.1:${OS_HTTP}/" "${OPENSEARCH_STARTUP_TIMEOUT_SECONDS}"; then
  write_report 0 false opensearch_startup_timeout
  exit 1
fi

collect_seed_peer_identity

steelsearch_env=(
  STEELSEARCH_HTTP_HOST=127.0.0.1
  STEELSEARCH_TRANSPORT_HOST=127.0.0.1
  STEELSEARCH_HTTP_ACCESS_HOST=127.0.0.1
  STEELSEARCH_TRANSPORT_ACCESS_HOST=127.0.0.1
  STEELSEARCH_HTTP_PORT="${SS_HTTP}"
  STEELSEARCH_TRANSPORT_PORT="${SS_TRANSPORT}"
  STEELSEARCH_CLUSTER_NAME="${CLUSTER_NAME}"
  STEELSEARCH_NODE_NAME="${RUST_NODE_NAME}"
  STEELSEARCH_NODE_ID="${RUST_NODE_NAME}"
  STEELSEARCH_DISCOVERY_SEED_HOSTS="${STEELSEARCH_SEEDS}"
  STEELSEARCH_WORK_DIR="${STEELSEARCH_WORK_DIR}"
)
if [[ -n "${JAVA_RUST_MIXED_MEMBERSHIP_STEELSEARCH_MODE:-}" ]]; then
  steelsearch_env+=(STEELSEARCH_MODE="${JAVA_RUST_MIXED_MEMBERSHIP_STEELSEARCH_MODE}")
fi
if [[ -n "${JAVA_RUST_MIXED_MEMBERSHIP_JAVA_WRITE_FORWARDING_VALIDATED:-}" ]]; then
  steelsearch_env+=(STEELSEARCH_JAVA_WRITE_FORWARDING_VALIDATED="${JAVA_RUST_MIXED_MEMBERSHIP_JAVA_WRITE_FORWARDING_VALIDATED}")
fi
if [[ -n "${JAVA_RUST_MIXED_MEMBERSHIP_STEELSEARCH_SPLIT_BUILD_RUN:-}" ]]; then
  steelsearch_env+=(STEELSEARCH_SPLIT_BUILD_RUN="${JAVA_RUST_MIXED_MEMBERSHIP_STEELSEARCH_SPLIT_BUILD_RUN}")
fi
if [[ -n "${JAVA_RUST_MIXED_MEMBERSHIP_STEELSEARCH_TRANSPORT_PRE_FIRST_FRAME_TIMEOUT_MS:-}" ]]; then
  steelsearch_env+=(
    STEELSEARCH_TRANSPORT_PRE_FIRST_FRAME_TIMEOUT_MS="${JAVA_RUST_MIXED_MEMBERSHIP_STEELSEARCH_TRANSPORT_PRE_FIRST_FRAME_TIMEOUT_MS}"
  )
fi
if [[ "${SKIP_SEED_PEER_IDENTITY_MANIFEST}" != "1" ]] && [[ -f "${TRANSPORT_IDENTITY_WORK_DIR}/transport-handshake-response-parsed.json" ]]; then
  steelsearch_env+=(STEELSEARCH_INTEROP_SEED_PEER_IDENTITY_MANIFEST="${TRANSPORT_IDENTITY_WORK_DIR}/transport-handshake-response-parsed.json")
fi
write_env_snapshot "${STEELSEARCH_WORK_DIR}/launch-env.json" "${steelsearch_env[@]}"
env "${steelsearch_env[@]}"   bash "${ROOT_DIR}/tools/run-steelsearch-dev.sh"   >"${STEELSEARCH_WORK_DIR}/stdout.log"   2>"${STEELSEARCH_WORK_DIR}/stderr.log" &
echo "$!" >"${STEELSEARCH_WORK_DIR}/pid"
printf '%s\n' "STEELSEARCH_HTTP_PORT=${SS_HTTP} STEELSEARCH_TRANSPORT_PORT=${SS_TRANSPORT} STEELSEARCH_NODE_NAME=${RUST_NODE_NAME} STEELSEARCH_CLUSTER_NAME=${CLUSTER_NAME} bash ${ROOT_DIR}/tools/run-steelsearch-dev.sh" >"${STEELSEARCH_WORK_DIR}/start-command.txt"

if [[ "${JAVA_RUST_MIXED_MEMBERSHIP_SKIP_ACTIVE_STEELSEARCH_PROBES:-0}" != "1" ]]; then
  for _ in $(seq 1 20); do
    if probe_steelsearch_transport >/dev/null 2>&1; then
      if python3 - "${STEELSEARCH_WORK_DIR}/transport-connect.json" <<'PY'
import json, sys
from pathlib import Path
report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
raise SystemExit(0 if report.get("tcp_connected") else 1)
PY
      then
        break
      fi
    fi
    sleep 1
  done
  probe_steelsearch_transport_handshake >/dev/null 2>&1 || true
fi

if [[ -n "${LIVE_HANDOFF_REPORT_PATH}" ]]; then
  EARLY_NODE_COUNT="$(current_node_count 2>/dev/null || echo 0)"
  write_report "${EARLY_NODE_COUNT}" false live_handoff_ready "${LIVE_HANDOFF_REPORT_PATH}"
fi

started_at="$(date +%s)"
while true; do
  node_count="$(current_node_count 2>/dev/null || echo 0)"
  if [[ "${node_count}" -ge 2 ]]; then
    break
  fi
  if (( $(date +%s) - started_at >= MEMBERSHIP_TIMEOUT_SECONDS )); then
    break
  fi
  sleep 1
done

NODE_COUNT="$(current_node_count 2>/dev/null || echo 0)"
if [[ "${NODE_COUNT}" -ge 2 ]]; then
  if [[ -n "${LIVE_HANDOFF_REPORT_PATH}" ]]; then
    write_report "${NODE_COUNT}" true none "${LIVE_HANDOFF_REPORT_PATH}"
  fi
  if [[ -n "${FORMED_HANDOFF_REPORT_PATH}" ]]; then
    write_report "${NODE_COUNT}" true none "${FORMED_HANDOFF_REPORT_PATH}"
  fi
  if [[ "${KEEP_ALIVE_SECONDS}" != "0" ]]; then
    sleep "${KEEP_ALIVE_SECONDS}"
  fi
  write_report "${NODE_COUNT}" true none
else
  write_report "${NODE_COUNT}" false membership_timeout
  exit 1
fi
