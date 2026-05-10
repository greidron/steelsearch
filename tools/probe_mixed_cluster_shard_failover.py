#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


class HttpJson:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        body: Any | None = None,
        expected: set[int] | None = None,
        timeout: float = 20.0,
    ) -> tuple[int, Any]:
        expected = expected or {200}
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=payload,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = response.status
                raw = response.read()
        except urllib.error.HTTPError as error:
            status = error.code
            raw = error.read()
        text = raw.decode("utf-8", errors="replace")
        try:
            data = json.loads(text) if text else {}
        except json.JSONDecodeError:
            data = {"raw": text}
        if status not in expected:
            raise AssertionError(f"{method} {path} returned {status}: {data}")
        return status, data


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def wait_for(predicate, attempts: int, sleep_seconds: float) -> bool:
    for _ in range(attempts):
        if predicate():
            return True
        time.sleep(sleep_seconds)
    return False


def wait_for_http(url: str, attempts: int, sleep_seconds: float) -> bool:
    client = HttpJson(url)
    return wait_for(lambda: _safe_root(client), attempts, sleep_seconds)


def _safe_root(client: HttpJson) -> bool:
    try:
        client.request("GET", "/", expected={200})
        return True
    except Exception:
        return False


def read_pid(pid_path: Path) -> int:
    return int(pid_path.read_text(encoding="utf-8").strip())


def terminate_pid(pid_path: Path) -> int:
    pid = read_pid(pid_path)
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return pid
    for _ in range(50):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return pid
        time.sleep(0.2)
    raise RuntimeError(f"pid {pid} did not exit after SIGTERM")


def restart_process(pid_path: Path, start_command_path: Path, stdout_path: Path, stderr_path: Path) -> int:
    start_cmd = start_command_path.read_text(encoding="utf-8").strip()
    stdout_handle = open(stdout_path, "ab")
    stderr_handle = open(stderr_path, "ab")
    proc = subprocess.Popen(
        ["/bin/bash", "-lc", start_cmd],
        stdout=stdout_handle,
        stderr=stderr_handle,
        preexec_fn=os.setsid,
    )
    pid_path.write_text(f"{proc.pid}\n", encoding="utf-8")
    return proc.pid


def get_shards(client: HttpJson, index: str) -> list[dict[str, Any]]:
    _, data = client.request(
        "GET",
        f"/_cat/shards/{urllib.parse.quote(index, safe='')}?format=json",
        expected={200},
    )
    if not isinstance(data, list):
        raise AssertionError(f"unexpected shard payload: {data}")
    return data


def get_search_count(client: HttpJson, index: str) -> int:
    _, data = client.request(
        "POST",
        f"/{urllib.parse.quote(index, safe='')}/_search",
        {"size": 0, "query": {"match_all": {}}},
        expected={200},
    )
    total = data.get("hits", {}).get("total", {})
    if isinstance(total, dict):
        return int(total.get("value", 0))
    if isinstance(total, int):
        return total
    return 0


def placement(shards: list[dict[str, Any]]) -> dict[str, str | None]:
    primary = next((row for row in shards if row.get("prirep") == "p"), None)
    replica = next((row for row in shards if row.get("prirep") == "r"), None)
    return {
        "primary_node": None if primary is None else primary.get("node"),
        "primary_state": None if primary is None else primary.get("state"),
        "replica_node": None if replica is None else replica.get("node"),
        "replica_state": None if replica is None else replica.get("state"),
    }


def reserve_unique_ports(count: int) -> list[int]:
    sockets: list[socket.socket] = []
    try:
        for _ in range(count):
            bound = socket.socket()
            bound.bind(("127.0.0.1", 0))
            sockets.append(bound)
        return [bound.getsockname()[1] for bound in sockets]
    finally:
        for bound in sockets:
            bound.close()


def create_probe_cluster(
    work_dir: Path,
    keep_alive_seconds: int,
    os_http_port: int,
    os_transport_port: int,
    ss_http_port: int,
    ss_transport_port: int,
) -> subprocess.Popen[bytes]:
    formed_report = work_dir / "formed-handoff.json"
    env = os.environ.copy()
    env.update(
        {
            "JAVA_RUST_MIXED_MEMBERSHIP_WORK_DIR": str(work_dir),
            "JAVA_RUST_MIXED_MEMBERSHIP_JAVA_WRITE_FORWARDING_VALIDATED": "true",
            "STEELSEARCH_SPLIT_BUILD_RUN": "1",
            "JAVA_RUST_MIXED_MEMBERSHIP_FORMED_HANDOFF_REPORT_PATH": str(formed_report),
            "JAVA_RUST_MIXED_MEMBERSHIP_KEEP_ALIVE_SECONDS": str(keep_alive_seconds),
            "JAVA_RUST_MIXED_MEMBERSHIP_OS_HTTP_PORT": str(os_http_port),
            "JAVA_RUST_MIXED_MEMBERSHIP_OS_TRANSPORT_PORT": str(os_transport_port),
            "JAVA_RUST_MIXED_MEMBERSHIP_SS_HTTP_PORT": str(ss_http_port),
            "JAVA_RUST_MIXED_MEMBERSHIP_SS_TRANSPORT_PORT": str(ss_transport_port),
        }
    )
    stdout = open(work_dir / "probe.stdout.log", "ab")
    stderr = open(work_dir / "probe.stderr.log", "ab")
    return subprocess.Popen(
        ["/bin/bash", "-lc", "bash tools/probe_java_rust_mixed_membership.sh"],
        cwd="/home/ubuntu/steelsearch",
        env=env,
        stdout=stdout,
        stderr=stderr,
        preexec_fn=os.setsid,
    )


def wait_for_membership(formed_report: Path, attempts: int, sleep_seconds: float) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for _ in range(attempts):
        if formed_report.exists():
            payload = read_json(formed_report)
            if payload.get("membership_formed") is True and payload.get("observed_node_count", 0) >= 2:
                return payload
        time.sleep(sleep_seconds)
    raise RuntimeError(f"timed out waiting for membership in {formed_report}")


def setup_index(java_client: HttpJson, index: str, doc_count: int) -> dict[str, Any]:
    java_client.request("DELETE", f"/{index}?ignore_unavailable=true", expected={200, 404})
    java_client.request(
        "PUT",
        f"/{index}",
        {"settings": {"index": {"number_of_shards": 1, "number_of_replicas": 1}}},
        expected={200},
    )
    for seq in range(doc_count):
        java_client.request(
            "PUT",
            f"/{index}/_doc/doc-{seq}",
            {"seq": seq, "message": f"mixed-doc-{seq}"},
            expected={200, 201},
        )
    java_client.request("POST", f"/{index}/_refresh", expected={200})
    _, health = java_client.request(
        "GET",
        f"/_cluster/health/{index}?wait_for_status=green&timeout=60s",
        expected={200},
        timeout=65.0,
    )
    return health


def phase_result(name: str, **kwargs: Any) -> dict[str, Any]:
    result = {"phase": name}
    result.update(kwargs)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", default="/tmp/mixed-cluster-shard-failover.latest")
    parser.add_argument("--index", default="mixed-shard-failover-000001")
    parser.add_argument("--doc-count", type=int, default=5)
    parser.add_argument("--keep-alive-seconds", type=int, default=240)
    args = parser.parse_args()

    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    formed_report = work_dir / "formed-handoff.json"
    report_path = work_dir / "shard-failover-report.json"
    os_http_port, os_transport_port, ss_http_port, ss_transport_port = reserve_unique_ports(4)

    probe_proc = create_probe_cluster(
        work_dir,
        args.keep_alive_seconds,
        os_http_port,
        os_transport_port,
        ss_http_port,
        ss_transport_port,
    )
    report: dict[str, Any] = {
        "work_dir": str(work_dir),
        "index": args.index,
        "doc_count": args.doc_count,
        "reserved_ports": {
            "opensearch_http": os_http_port,
            "opensearch_transport": os_transport_port,
            "steelsearch_http": ss_http_port,
            "steelsearch_transport": ss_transport_port,
        },
        "phases": [],
        "summary": {"passed": False},
    }

    try:
        handoff = wait_for_membership(formed_report, attempts=180, sleep_seconds=1.0)
        artifacts = handoff["artifacts"]
        java_url = handoff["success_harness_handoff"]["cluster_url"]
        rust_launch_env = read_json(Path(artifacts["steelsearch_launch_env"]))
        rust_url = f"http://127.0.0.1:{rust_launch_env['STEELSEARCH_HTTP_PORT']}"

        java_client = HttpJson(java_url)
        rust_client = HttpJson(rust_url)

        report["handoff"] = {
            "java_url": java_url,
            "rust_url": rust_url,
            "java_node": handoff["success_harness_handoff"]["java_node"],
            "rust_node": handoff["success_harness_handoff"]["rust_node"],
        }

        health = setup_index(java_client, args.index, args.doc_count)
        initial_shards = get_shards(java_client, args.index)
        initial_placement = placement(initial_shards)
        initial_search_count = get_search_count(java_client, args.index)
        report["phases"].append(
            phase_result(
                "initial",
                cluster_health=health.get("status"),
                shards=initial_shards,
                placement=initial_placement,
                search_count=initial_search_count,
            )
        )

        java_pid_path = Path(artifacts["opensearch_pid"])
        java_start_command_path = Path(artifacts["opensearch_start_command"])
        java_stdout_path = Path(artifacts["opensearch_stdout"])
        java_stderr_path = Path(artifacts["opensearch_stderr"])
        rust_pid_path = Path(artifacts["steelsearch_pid"])
        rust_start_command_path = Path(artifacts["steelsearch_start_command"])
        rust_stdout_path = Path(artifacts["steelsearch_stdout"])
        rust_stderr_path = Path(artifacts["steelsearch_stderr"])

        terminated_java_pid = terminate_pid(java_pid_path)
        rust_http_ready = wait_for_http(rust_url, attempts=60, sleep_seconds=1.0)
        java_to_rust: dict[str, Any] = {
            "terminated_java_pid": terminated_java_pid,
            "rust_http_ready": rust_http_ready,
        }
        if rust_http_ready:
            rust_shards = get_shards(rust_client, args.index)
            rust_count = get_search_count(rust_client, args.index)
            java_to_rust["shards"] = rust_shards
            java_to_rust["placement"] = placement(rust_shards)
            java_to_rust["search_count"] = rust_count
            java_to_rust["passed"] = (
                rust_count == args.doc_count
                and java_to_rust["placement"]["primary_node"] == handoff["success_harness_handoff"]["rust_node"]
            )
        else:
            java_to_rust["passed"] = False
        report["phases"].append(phase_result("java_to_steelsearch", **java_to_rust))

        restarted_java_pid = restart_process(
            java_pid_path,
            java_start_command_path,
            java_stdout_path,
            java_stderr_path,
        )
        java_http_ready = wait_for_http(java_url, attempts=90, sleep_seconds=1.0)
        reform = {
            "restarted_java_pid": restarted_java_pid,
            "java_http_ready": java_http_ready,
        }
        if java_http_ready:
            reform["shards"] = get_shards(java_client, args.index)
            reform["placement"] = placement(reform["shards"])
            reform["search_count"] = get_search_count(java_client, args.index)
        report["phases"].append(phase_result("java_rejoin", **reform))

        terminated_rust_pid = terminate_pid(rust_pid_path)
        java_http_after_rust_stop = wait_for_http(java_url, attempts=60, sleep_seconds=1.0)
        rust_to_java: dict[str, Any] = {
            "terminated_rust_pid": terminated_rust_pid,
            "java_http_ready": java_http_after_rust_stop,
        }
        if java_http_after_rust_stop:
            java_shards = get_shards(java_client, args.index)
            java_count = get_search_count(java_client, args.index)
            rust_to_java["shards"] = java_shards
            rust_to_java["placement"] = placement(java_shards)
            rust_to_java["search_count"] = java_count
            rust_to_java["passed"] = (
                java_count == args.doc_count
                and rust_to_java["placement"]["primary_node"] == handoff["success_harness_handoff"]["java_node"]
            )
        else:
            rust_to_java["passed"] = False
        report["phases"].append(phase_result("steelsearch_to_opensearch", **rust_to_java))

        report["summary"] = {
            "passed": bool(java_to_rust.get("passed")) and bool(rust_to_java.get("passed")),
            "java_to_steelsearch_passed": bool(java_to_rust.get("passed")),
            "steelsearch_to_opensearch_passed": bool(rust_to_java.get("passed")),
        }
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0 if report["summary"]["passed"] else 1
    finally:
        try:
            os.killpg(os.getpgid(probe_proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            probe_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(probe_proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass


if __name__ == "__main__":
    sys.exit(main())
