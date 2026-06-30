#!/usr/bin/env python3
"""Compare Steelsearch remote_transport backpressure with an OpenSearch peer."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPENSEARCH_DIST = Path(
    "/home/ubuntu/OpenSearch/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("dry-run", "steelsearch", "opensearch", "both"), default="dry-run")
    parser.add_argument(
        "--profile",
        choices=("same-host-query-pressure", "mixed-java-rust-query-phase"),
        default="same-host-query-pressure",
        help="comparison contract to declare in the generated report",
    )
    parser.add_argument("--work-dir", default="/tmp/remote-transport-backpressure-compare")
    parser.add_argument("--opensearch-dist-home", default=str(DEFAULT_OPENSEARCH_DIST))
    parser.add_argument("--output", help="write JSON report to this path")
    parser.add_argument("--keep-work-dir", action="store_true")
    args = parser.parse_args()

    if args.mode == "dry-run":
        report = {
            "summary": {
                "passed": True,
                "mode": args.mode,
                "profile": args.profile,
                "checks": [
                    "steelsearch_remote_transport_active_rejected_completed_rest_readback",
                    "opensearch_search_thread_pool_rejected_completed_rest_readback",
                ],
            },
            "profile": comparison_profile(args.profile),
        }
        emit(report, args.output)
        return 0

    work_dir = Path(args.work_dir)
    if work_dir.exists() and not args.keep_work_dir:
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, Any] = {}
    try:
        if args.mode in ("steelsearch", "both"):
            results["steelsearch"] = run_steelsearch_probe(work_dir / "steelsearch")
        if args.mode in ("opensearch", "both"):
            results["opensearch"] = run_opensearch_probe(Path(args.opensearch_dist_home), work_dir / "opensearch")
    finally:
        if not args.keep_work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)

    expected = []
    if "steelsearch" in results:
        expected.append(results["steelsearch"]["passed"])
    if "opensearch" in results:
        expected.append(results["opensearch"]["passed"])
    passed = bool(expected) and all(expected)
    report = {
        "summary": {
            "passed": passed,
            "mode": args.mode,
            "profile": args.profile,
            "steelsearch_passed": results.get("steelsearch", {}).get("passed"),
            "opensearch_passed": results.get("opensearch", {}).get("passed"),
            "comparison": (
                "Steelsearch remote_transport rejects/readbacks queued query-phase transport work; "
                "OpenSearch peer rejects/readbacks saturated search thread-pool work under equivalent query pressure."
            ),
        },
        "profile": comparison_profile(args.profile),
        "results": results,
    }
    emit(report, args.output)
    return 0 if passed else 1


def run_steelsearch_probe(work_dir: Path) -> dict[str, Any]:
    binary = build_steelsearch()
    work_dir.mkdir(parents=True, exist_ok=True)
    http_ports = [free_port() for _ in range(3)]
    transport_ports = [free_port() for _ in range(3)]
    seed_hosts = ",".join(f"127.0.0.1:{port}" for port in transport_ports)
    children: list[subprocess.Popen[Any]] = []
    try:
        for index in range(3):
            node_dir = work_dir / f"node-{index + 1}"
            (node_dir / "data").mkdir(parents=True, exist_ok=True)
            (node_dir / "logs").mkdir(parents=True, exist_ok=True)
            stdout = open(node_dir / "logs" / "stdout.log", "wb")
            stderr = open(node_dir / "logs" / "stderr.log", "wb")
            env = os.environ.copy()
            env.update(
                {
                    "STEELSEARCH_REMOTE_TRANSPORT_MAX_IN_FLIGHT": "1",
                    "STEELSEARCH_REMOTE_TRANSPORT_QUEUE_SIZE": "0",
                    "STEELSEARCH_REMOTE_TRANSPORT_QUERY_PHASE_PAUSE_MILLIS": "1000",
                }
            )
            children.append(
                subprocess.Popen(
                    [
                        str(binary),
                        "--http.host",
                        "127.0.0.1",
                        "--http.port",
                        str(http_ports[index]),
                        "--transport.host",
                        "127.0.0.1",
                        "--transport.port",
                        str(transport_ports[index]),
                        "--node.id",
                        f"steel-node-{index + 1}",
                        "--node.name",
                        f"steel-node-{index + 1}",
                        "--cluster.name",
                        "steel-remote-backpressure-compare",
                        "--node.roles",
                        "cluster_manager,data,ingest",
                        "--discovery.seed_hosts",
                        seed_hosts,
                        "--path.data",
                        str(node_dir / "data"),
                    ],
                    cwd=ROOT,
                    env=env,
                    stdout=stdout,
                    stderr=stderr,
                )
            )

        for port in http_ports:
            wait_for_json(
                f"http://127.0.0.1:{port}/_steelsearch/dev/cluster",
                lambda body: body.get("cluster_name") == "steel-remote-backpressure-compare"
                and len(body.get("nodes", [])) == 3
                and body.get("coordination", {}).get("publication_committed") is True,
                timeout=45,
            )

        target_http_port = http_ports[0]
        target_transport_port = transport_ports[0]
        first = threading.Thread(
            target=send_query_phase_transport_frame,
            args=(target_transport_port, 20_001, 1.2),
            daemon=True,
        )
        first.start()
        active_row = wait_for_cat_counter(target_http_port, "active", lambda value: int(value) >= 1)
        send_query_phase_transport_frame(target_transport_port, 20_002, 0.05)
        rejected_row = wait_for_cat_counter(target_http_port, "rejected", lambda value: int(value) >= 1)
        first.join(timeout=5)
        completed_row = wait_for_cat_counter(target_http_port, "completed", lambda value: int(value) >= 1)
        stats = http_json(f"http://127.0.0.1:{target_http_port}/_nodes/stats")
        pool = stats["nodes"]["steel-node-1"]["thread_pool"]["remote_transport"]
        passed = int(pool["rejected"]) >= 1 and int(pool["completed"]) >= 1
        return {
            "passed": passed,
            "pressure_surface": "mixed-cluster Rust query-phase remote transport admission",
            "pool": "remote_transport",
            "active_row": active_row,
            "rejected_row": rejected_row,
            "completed_row": completed_row,
            "node_stats": pool,
        }
    finally:
        terminate_all(children)


def run_opensearch_probe(dist_home: Path, work_dir: Path) -> dict[str, Any]:
    binary = dist_home / "bin" / "opensearch"
    if not binary.exists():
        raise FileNotFoundError(f"OpenSearch binary not found: {binary}")
    http_port = free_port()
    transport_port = free_port()
    data_dir = work_dir / "data"
    logs_dir = work_dir / "logs"
    repo_dir = work_dir / "repo"
    data_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    repo_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if "OPENSEARCH_JAVA_HOME" not in env:
        java = shutil.which("java")
        if java:
            env["OPENSEARCH_JAVA_HOME"] = str(Path(java).resolve().parents[1])
    env["OPENSEARCH_JAVA_OPTS"] = env.get("OPENSEARCH_JAVA_OPTS", "-Xms512m -Xmx512m")
    process = subprocess.Popen(
        [
            str(binary),
            f"-Epath.data={data_dir}",
            f"-Epath.logs={logs_dir}",
            f"-Epath.repo={repo_dir}",
            "-Ehttp.host=127.0.0.1",
            f"-Ehttp.port={http_port}",
            "-Etransport.host=127.0.0.1",
            f"-Etransport.port={transport_port}",
            "-Ecluster.name=opensearch-remote-backpressure-compare",
            "-Enode.name=opensearch-backpressure-node",
            "-Ediscovery.type=single-node",
            "-Ethread_pool.search.size=1",
            "-Ethread_pool.search.queue_size=1",
            "-Ecluster.routing.allocation.disk.threshold_enabled=false",
        ],
        cwd=ROOT,
        env=env,
        stdout=open(logs_dir / "stdout.log", "wb"),
        stderr=subprocess.STDOUT,
    )
    base_url = f"http://127.0.0.1:{http_port}"
    try:
        root = wait_for_json(base_url, lambda body: body.get("tagline", "").startswith("The OpenSearch Project"), 120)
        index = "remote-backpressure-compare"
        http_json(f"{base_url}/{index}", method="DELETE", tolerate_status=(404,))
        http_json(
            f"{base_url}/{index}",
            method="PUT",
            body={
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {"properties": {"n": {"type": "integer"}, "text": {"type": "text"}}},
            },
        )
        bulk_lines = []
        for i in range(5000):
            bulk_lines.append(json.dumps({"index": {"_index": index, "_id": str(i)}}))
            bulk_lines.append(json.dumps({"n": i, "text": f"alpha beta gamma delta epsilon {i}"}))
        http_raw(f"{base_url}/_bulk?refresh=true", "\n".join(bulk_lines).encode() + b"\n", "application/x-ndjson")
        before = cat_pool(base_url, "search")
        errors = run_opensearch_search_pressure(base_url, index)
        after = cat_pool(base_url, "search")
        stats = http_json(f"{base_url}/_nodes/stats/thread_pool")
        node_stats = next(iter(stats["nodes"].values()))["thread_pool"]["search"]
        rejected_errors = [error for error in errors if error.get("status") == 429]
        passed = int(after["rejected"]) > int(before["rejected"]) and int(node_stats["rejected"]) > 0
        return {
            "passed": passed,
            "pressure_surface": "Java peer search thread-pool query execution",
            "pool": "search",
            "version": root.get("version", {}),
            "before_row": before,
            "after_row": after,
            "node_stats": node_stats,
            "http_429_count": len(rejected_errors),
            "error_samples": rejected_errors[:3],
        }
    finally:
        terminate_all([process])


def comparison_profile(name: str) -> dict[str, Any]:
    profiles = {
        "same-host-query-pressure": {
            "name": "same-host-query-pressure",
            "scope": "same-host Steelsearch/OpenSearch pressure comparison",
            "participants": [
                "standalone Steelsearch three-daemon Rust cluster",
                "standalone single-node OpenSearch Java peer",
            ],
            "steelsearch_surface": "remote_transport query-phase route admission",
            "opensearch_surface": "search thread-pool query execution",
            "required_readbacks": [
                "Steelsearch _cat/thread_pool/remote_transport rejected>=1",
                "Steelsearch _nodes/stats thread_pool.remote_transport completed>=1",
                "OpenSearch _cat/thread_pool/search rejected increases",
                "OpenSearch _nodes/stats/thread_pool search rejected>0",
            ],
        },
        "mixed-java-rust-query-phase": {
            "name": "mixed-java-rust-query-phase",
            "scope": "declared mixed-cluster Java/Rust query-phase backpressure profile",
            "participants": [
                "Rust Steelsearch data-node query-phase receiver",
                "Java OpenSearch peer search coordinator pressure analogue",
            ],
            "steelsearch_surface": "indices:data/read/search[phase/query] over remote_transport",
            "opensearch_surface": "Java search thread-pool saturation under equivalent query pressure",
            "required_readbacks": [
                "Rust receiver rejects excess query-phase remote transport work",
                "Rust receiver exposes remote_transport rejected/completed through _cat and _nodes/stats",
                "Java peer exposes analogous search thread-pool rejection through _cat and _nodes/stats",
                "profile report records both surfaces through live transport and REST counter readbacks",
            ],
            "limits": [
                "the comparison runs independent local Rust and Java probes unless a future harness supplies a live mixed-cluster coordinator",
                "the profile is parity evidence for query-phase backpressure semantics",
            ],
        },
    }
    return profiles[name]


def run_opensearch_search_pressure(base_url: str, index: str) -> list[dict[str, Any]]:
    query = {
        "query": {
            "script": {
                "script": {
                    "lang": "painless",
                    "source": (
                        "long x=0; for (int i=0; i<params.loops; ++i) { x += i; } "
                        "return doc['n'].value >= 0;"
                    ),
                    "params": {"loops": 20_000},
                }
            }
        },
        "size": 10,
    }
    errors: list[dict[str, Any]] = []
    lock = threading.Lock()

    def worker() -> None:
        for _ in range(5):
            try:
                http_json(f"{base_url}/{index}/_search", method="POST", body=query, timeout=30)
            except HttpError as error:
                with lock:
                    errors.append({"status": error.status, "body": error.body})

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(32)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return errors


def build_steelsearch() -> Path:
    subprocess.run(
        ["cargo", "build", "-p", "os-node", "--features", "standalone-runtime", "--bin", "steelsearch"],
        cwd=ROOT,
        check=True,
    )
    return ROOT / "target" / "debug" / "steelsearch"


def send_query_phase_transport_frame(port: int, request_id: int, hold_seconds: float) -> None:
    frame = build_transport_request_frame(request_id, "indices:data/read/search[phase/query]")
    with socket.create_connection(("127.0.0.1", port), timeout=2) as sock:
        sock.sendall(frame)
        time.sleep(hold_seconds)


def build_transport_request_frame(request_id: int, action: str) -> bytes:
    variable_header = bytearray()
    write_vint(variable_header, 0)
    write_vint(variable_header, 0)
    write_vint(variable_header, 0)
    write_string(variable_header, action)
    message_length = 8 + 1 + 4 + 4 + len(variable_header)
    frame = bytearray()
    frame.extend(b"ES")
    frame.extend(message_length.to_bytes(4, "big"))
    frame.extend(request_id.to_bytes(8, "big", signed=True))
    frame.append(0)
    frame.extend((3_070_099).to_bytes(4, "big"))
    frame.extend(len(variable_header).to_bytes(4, "big"))
    frame.extend(variable_header)
    return bytes(frame)


def write_string(out: bytearray, value: str) -> None:
    data = value.encode()
    write_vint(out, len(data))
    out.extend(data)


def write_vint(out: bytearray, value: int) -> None:
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)


def wait_for_cat_counter(port: int, counter: str, predicate: Any) -> dict[str, Any]:
    deadline = time.monotonic() + 10
    last_row = None
    while time.monotonic() < deadline:
        rows = http_json(
            "http://127.0.0.1:"
            f"{port}/_cat/thread_pool/remote_transport?format=json"
            "&h=node_id,node_name,name,active,queue,rejected,completed"
        )
        for row in rows:
            if row.get("node_id") == "steel-node-1" or row.get("node_name") == "steel-node-1":
                last_row = row
                if predicate(row[counter]):
                    return row
        time.sleep(0.05)
    raise TimeoutError(f"remote_transport {counter} did not match predicate; last row={last_row}")


def cat_pool(base_url: str, pool: str) -> dict[str, Any]:
    rows = http_json(f"{base_url}/_cat/thread_pool/{pool}?format=json")
    if not rows:
        raise RuntimeError(f"missing _cat/thread_pool/{pool} row")
    return rows[0]


def wait_for_json(url: str, predicate: Any, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            body = http_json(url, timeout=2)
            if predicate(body):
                return body
        except Exception as error:  # noqa: BLE001 - surface last startup failure.
            last_error = error
        time.sleep(1)
    raise TimeoutError(f"{url} did not become ready; last error={last_error}")


class HttpError(RuntimeError):
    def __init__(self, status: int, body: Any) -> None:
        super().__init__(f"HTTP {status}: {body}")
        self.status = status
        self.body = body


def http_json(
    url: str,
    *,
    method: str = "GET",
    body: Any | None = None,
    timeout: float = 10,
    tolerate_status: tuple[int, ...] = (),
) -> Any:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return json.loads(raw or b"{}")
    except urllib.error.HTTPError as error:
        raw = error.read()
        parsed = json.loads(raw or b"{}")
        if error.code in tolerate_status:
            return parsed
        raise HttpError(error.code, parsed) from error


def http_raw(url: str, data: bytes, content_type: str) -> Any:
    request = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": content_type})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read() or b"{}")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def terminate_all(processes: list[subprocess.Popen[Any]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    deadline = time.monotonic() + 10
    for process in processes:
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.1)
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def emit(report: dict[str, Any], output: str | None) -> None:
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output:
        Path(output).write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    sys.exit(main())
