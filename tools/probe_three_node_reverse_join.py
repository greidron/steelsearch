#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Any


def reserve_unique_ports(count: int) -> list[int]:
    holders: list[socket.socket] = []
    try:
        for _ in range(count):
            bound = socket.socket()
            bound.bind(("127.0.0.1", 0))
            holders.append(bound)
        return [bound.getsockname()[1] for bound in holders]
    finally:
        for bound in holders:
            bound.close()


def make_env(extra: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    env.update(extra)
    return env


def start_process(command: str, env: dict[str, str], stdout_path: Path, stderr_path: Path) -> subprocess.Popen[bytes]:
    stdout_handle = stdout_path.open("ab")
    stderr_handle = stderr_path.open("ab")
    return subprocess.Popen(
        ["/bin/bash", "-lc", command],
        cwd="/home/ubuntu/steelsearch",
        env=env,
        stdout=stdout_handle,
        stderr=stderr_handle,
        preexec_fn=os.setsid,
    )


def terminate_process(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        proc.wait(timeout=10)


def wait_for_http(url: str, attempts: int) -> bool:
    import urllib.request

    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=2.0) as response:
                if response.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1.0)
    return False


def run_logged(command: str, log_path: Path) -> None:
    with log_path.open("ab") as handle:
        subprocess.run(
            ["/bin/bash", "-lc", command],
            cwd="/home/ubuntu/steelsearch",
            stdout=handle,
            stderr=handle,
            check=True,
        )


def collect_seed_identity(identity_dir: Path, java_transport_port: int) -> Path:
    identity_dir.mkdir(parents=True, exist_ok=True)
    frame_dump = subprocess.run(
        ["/bin/bash", "-lc", "bash tools/dump_java_transport_handshake_frame.sh"],
        cwd="/home/ubuntu/steelsearch",
        capture_output=True,
        text=True,
        check=True,
    )
    frame_hex = frame_dump.stdout.strip()
    report_path = identity_dir / "transport-handshake-report.json"
    parsed_path = identity_dir / "transport-handshake-response-parsed.json"
    run_logged(
        "python3 tools/send_opensearch_tcp_handshake_probe.py "
        f"--host 127.0.0.1 --port {java_transport_port} "
        "--action internal:transport/handshake "
        f"--frame-hex {frame_hex} "
        "--timeout-seconds 2.0 "
        f"--report-path {report_path}",
        identity_dir / "probe.log",
    )
    response_hex = json.loads(report_path.read_text(encoding="utf-8")).get("response_hex", "")
    if not response_hex:
        raise RuntimeError("failed to collect Java seed identity")
    run_logged(
        f"bash tools/parse_java_transport_handshake_response.sh --response-hex {response_hex} --report-path {parsed_path}",
        identity_dir / "parse.log",
    )
    return parsed_path


def curl_json(url: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["/bin/bash", "-lc", f"curl -fsS {url!s}"],
        cwd="/home/ubuntu/steelsearch",
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return {"ok": False, "error": completed.stderr.strip() or completed.stdout.strip()}
    try:
        return {"ok": True, "data": json.loads(completed.stdout)}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "raw": completed.stdout}


def main() -> int:
    work_dir = Path("/tmp/three-node-reverse-join.latest")
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    rust_dir = work_dir / "rust-replica-1"
    java1_dir = work_dir / "java-primary-1"
    java2_dir = work_dir / "java-primary-2"
    for path in (rust_dir, java1_dir, java2_dir):
        path.mkdir(parents=True, exist_ok=True)

    rust_http, rust_transport, java1_http, java1_transport, java2_http, java2_transport = reserve_unique_ports(6)
    seeds = f"127.0.0.1:{rust_transport},127.0.0.1:{java1_transport},127.0.0.1:{java2_transport}"
    initial_managers = "rust-replica-1,java-primary-1,java-primary-2"

    rust_proc = None
    java1_proc = None
    java2_proc = None
    seed_java_proc = None
    report: dict[str, Any] = {
        "work_dir": str(work_dir),
        "ports": {
            "rust_http": rust_http,
            "rust_transport": rust_transport,
            "java1_http": java1_http,
            "java1_transport": java1_transport,
            "java2_http": java2_http,
            "java2_transport": java2_transport,
        },
        "summary": {"passed": False},
    }
    try:
        seed_java_dir = work_dir / "seed-java"
        seed_java_dir.mkdir(parents=True, exist_ok=True)
        seed_java_proc = start_process(
            "bash tools/run-opensearch-dev.sh",
            make_env(
                {
                    "OPENSEARCH_HTTP_PORT": str(java1_http),
                    "OPENSEARCH_TRANSPORT_PORT": str(java1_transport),
                    "OPENSEARCH_CLUSTER_NAME": "mixed-three-node-reverse-dev",
                    "OPENSEARCH_NODE_NAME": "java-seed",
                    "OPENSEARCH_DISCOVERY_SEED_HOSTS": f"127.0.0.1:{java1_transport}",
                    "OPENSEARCH_INITIAL_CLUSTER_MANAGER_NODES": "java-seed",
                    "OPENSEARCH_WORK_DIR": str(seed_java_dir),
                }
            ),
            seed_java_dir / "stdout.log",
            seed_java_dir / "stderr.log",
        )
        if not wait_for_http(f"http://127.0.0.1:{java1_http}", attempts=45):
            raise RuntimeError("seed java did not start")
        seed_identity = collect_seed_identity(work_dir / "transport-identity", java1_transport)
        terminate_process(seed_java_proc)
        seed_java_proc = None
        shutil.rmtree(seed_java_dir)

        rust_proc = start_process(
            "bash tools/run-steelsearch-dev.sh",
            make_env(
                {
                    "STEELSEARCH_HTTP_HOST": "127.0.0.1",
                    "STEELSEARCH_TRANSPORT_HOST": "127.0.0.1",
                    "STEELSEARCH_HTTP_ACCESS_HOST": "127.0.0.1",
                    "STEELSEARCH_TRANSPORT_ACCESS_HOST": "127.0.0.1",
                    "STEELSEARCH_HTTP_PORT": str(rust_http),
                    "STEELSEARCH_TRANSPORT_PORT": str(rust_transport),
                    "STEELSEARCH_CLUSTER_NAME": "mixed-three-node-reverse-dev",
                    "STEELSEARCH_NODE_NAME": "rust-replica-1",
                    "STEELSEARCH_NODE_ID": "rust-replica-1",
                    "STEELSEARCH_DISCOVERY_SEED_HOSTS": seeds,
                    "STEELSEARCH_WORK_DIR": str(rust_dir),
                    "STEELSEARCH_JAVA_WRITE_FORWARDING_VALIDATED": "true",
                    "STEELSEARCH_SPLIT_BUILD_RUN": "1",
                    "STEELSEARCH_INTEROP_SEED_PEER_IDENTITY_MANIFEST": str(seed_identity),
                }
            ),
            rust_dir / "stdout.log",
            rust_dir / "stderr.log",
        )
        if not wait_for_http(f"http://127.0.0.1:{rust_http}", attempts=45):
            raise RuntimeError("rust did not start")

        java1_proc = start_process(
            "bash tools/run-opensearch-dev.sh",
            make_env(
                {
                    "OPENSEARCH_HTTP_PORT": str(java1_http),
                    "OPENSEARCH_TRANSPORT_PORT": str(java1_transport),
                    "OPENSEARCH_CLUSTER_NAME": "mixed-three-node-reverse-dev",
                    "OPENSEARCH_NODE_NAME": "java-primary-1",
                    "OPENSEARCH_DISCOVERY_SEED_HOSTS": seeds,
                    "OPENSEARCH_INITIAL_CLUSTER_MANAGER_NODES": initial_managers,
                    "OPENSEARCH_WORK_DIR": str(java1_dir),
                }
            ),
            java1_dir / "stdout.log",
            java1_dir / "stderr.log",
        )
        if not wait_for_http(f"http://127.0.0.1:{java1_http}", attempts=45):
            raise RuntimeError("java1 did not start")

        java2_proc = start_process(
            "bash tools/run-opensearch-dev.sh",
            make_env(
                {
                    "OPENSEARCH_HTTP_PORT": str(java2_http),
                    "OPENSEARCH_TRANSPORT_PORT": str(java2_transport),
                    "OPENSEARCH_CLUSTER_NAME": "mixed-three-node-reverse-dev",
                    "OPENSEARCH_NODE_NAME": "java-primary-2",
                    "OPENSEARCH_DISCOVERY_SEED_HOSTS": seeds,
                    "OPENSEARCH_INITIAL_CLUSTER_MANAGER_NODES": initial_managers,
                    "OPENSEARCH_WORK_DIR": str(java2_dir),
                }
            ),
            java2_dir / "stdout.log",
            java2_dir / "stderr.log",
        )
        if not wait_for_http(f"http://127.0.0.1:{java2_http}", attempts=45):
            raise RuntimeError("java2 did not start")

        time.sleep(45)
        report["rust_view"] = {
            "membership": json.loads((rust_dir / "data" / "production-membership.json").read_text(encoding="utf-8"))
            if (rust_dir / "data" / "production-membership.json").exists()
            else None,
            "gateway_state": json.loads((rust_dir / "data" / "gateway-state.json").read_text(encoding="utf-8"))
            if (rust_dir / "data" / "gateway-state.json").exists()
            else None,
        }
        report["java1_view"] = curl_json(f"http://127.0.0.1:{java1_http}/_cat/nodes?format=json")
        report["java2_view"] = curl_json(f"http://127.0.0.1:{java2_http}/_cat/nodes?format=json")
        java1_nodes = report["java1_view"].get("data", [])
        java2_nodes = report["java2_view"].get("data", [])
        rust_member_count = len(report["rust_view"]["membership"]["members"]) if report["rust_view"]["membership"] else 0
        report["summary"] = {
            "passed": len(java1_nodes) >= 3 and len(java2_nodes) >= 3,
            "java1_node_count": len(java1_nodes),
            "java2_node_count": len(java2_nodes),
            "rust_membership_count": rust_member_count,
        }
    except Exception as exc:
        report["failure_context"] = {
            "rust_view": {
                "membership": json.loads((rust_dir / "data" / "production-membership.json").read_text(encoding="utf-8"))
                if (rust_dir / "data" / "production-membership.json").exists()
                else None,
                "gateway_state": json.loads((rust_dir / "data" / "gateway-state.json").read_text(encoding="utf-8"))
                if (rust_dir / "data" / "gateway-state.json").exists()
                else None,
            },
            "java1_view": curl_json(f"http://127.0.0.1:{java1_http}/_cat/nodes?format=json"),
            "java2_view": curl_json(f"http://127.0.0.1:{java2_http}/_cat/nodes?format=json"),
        }
        report["summary"] = {"passed": False, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        report_path = work_dir / "report.json"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        terminate_process(java2_proc)
        terminate_process(java1_proc)
        terminate_process(seed_java_proc)
        terminate_process(rust_proc)
    return 0 if report["summary"].get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
