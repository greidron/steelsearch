#!/usr/bin/env python3
"""Generate Steelsearch-vs-OpenSearch HTTP load comparison evidence."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "target/release-load-comparison/http-load-comparison.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--steelsearch-binary", type=Path, default=ROOT / "target/release/steelsearch")
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--duration-seconds", type=float, default=30.0)
    parser.add_argument("--clients", type=int, default=4)
    parser.add_argument("--corpus-size", type=int, default=256)
    parser.add_argument("--vector-dimension", type=int, default=8)
    parser.add_argument("--query-mix", default="write=25,lexical=25,ranking=20,facet=15,sort_filter=10,refresh=5")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = generate_report(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.dry_run:
        return 0
    return 0 if report.get("summary", {}).get("error_count") == 0 else 1


def generate_report(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    work_dir = args.work_dir or Path(tempfile.mkdtemp(prefix="steelsearch-load-comparison.", dir=str(root / "target")))
    steel_http = free_port("127.0.0.1")
    steel_transport = free_port("127.0.0.1")
    open_http = free_port("127.0.0.1")
    open_transport = free_port("127.0.0.1")
    steel_command = build_steelsearch_command(
        binary=args.steelsearch_binary if args.steelsearch_binary.is_absolute() else root / args.steelsearch_binary,
        work_dir=work_dir / "steelsearch",
        http_port=steel_http,
        transport_port=steel_transport,
    )
    opensearch_command = build_opensearch_command(
        root=root,
        work_dir=work_dir / "opensearch",
        http_port=open_http,
        transport_port=open_transport,
    )
    comparison_command = build_comparison_command(
        root=root,
        output=args.output,
        steel_http=steel_http,
        open_http=open_http,
        duration_seconds=args.duration_seconds,
        clients=args.clients,
        corpus_size=args.corpus_size,
        vector_dimension=args.vector_dimension,
        query_mix=args.query_mix,
    )
    if args.dry_run:
        return {
            "dry_run": True,
            "steelsearch_command": [str(part) for part in steel_command],
            "opensearch_command": [str(part) for part in opensearch_command],
            "comparison_command": [str(part) for part in comparison_command],
            "output": str(args.output),
            "work_dir": str(work_dir),
        }

    steel_binary = Path(steel_command[0])
    if not steel_binary.is_file():
        write_failed_output(args.output, f"steelsearch binary is missing: {steel_binary}")
        return load_json(args.output)

    work_dir.mkdir(parents=True, exist_ok=True)
    steel_env = os.environ.copy()
    steel_env["STEELSEARCH_DATA_PATH"] = str(work_dir / "steelsearch" / "data")
    steel_env["STEELSEARCH_LOG_PATH"] = str(work_dir / "steelsearch" / "logs")
    (work_dir / "steelsearch" / "logs").mkdir(parents=True, exist_ok=True)
    (work_dir / "opensearch").mkdir(parents=True, exist_ok=True)
    with (work_dir / "steelsearch.log").open("w", encoding="utf-8") as steel_log:
        steel = subprocess.Popen(
            steel_command,
            cwd=root,
            env=steel_env,
            stdout=steel_log,
            stderr=subprocess.STDOUT,
            text=True,
        )
    open_env = {
        **os.environ,
        "OPENSEARCH_HTTP_HOST": "127.0.0.1",
        "OPENSEARCH_HTTP_PORT": str(open_http),
        "OPENSEARCH_TRANSPORT_HOST": "127.0.0.1",
        "OPENSEARCH_TRANSPORT_PORT": str(open_transport),
        "OPENSEARCH_WORK_DIR": str(work_dir / "opensearch"),
        "OPENSEARCH_CLUSTER_NAME": "opensearch-release-load",
        "OPENSEARCH_NODE_NAME": "opensearch-release-load-node",
    }
    with (work_dir / "opensearch.log").open("w", encoding="utf-8") as open_log:
        opensearch = subprocess.Popen(
            opensearch_command,
            cwd=root,
            env=open_env,
            stdout=open_log,
            stderr=subprocess.STDOUT,
            text=True,
        )
    try:
        wait_for_health(steel_http, timeout_seconds=60.0)
        wait_for_health(open_http, timeout_seconds=180.0)
        clear_opensearch_cluster_blocks(open_http, timeout_seconds=10.0)
        completed = subprocess.run(
            comparison_command,
            cwd=root,
            env={**os.environ, "RUN_HTTP_LOAD_COMPARISON": "1"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0 and not args.output.is_file():
            write_failed_output(
                args.output,
                f"load comparison failed: returncode={completed.returncode}",
                stderr_tail=completed.stderr[-4000:],
            )
        report = load_json(args.output)
        return persist_summary(args.output, report, returncode=completed.returncode, stderr_tail=completed.stderr[-4000:])
    finally:
        terminate(steel)
        terminate(opensearch)


def build_steelsearch_command(binary: Path, work_dir: Path, http_port: int, transport_port: int) -> list[str]:
    return [
        str(binary),
        "--http.host",
        "127.0.0.1",
        "--http.port",
        str(http_port),
        "--transport.host",
        "127.0.0.1",
        "--transport.port",
        str(transport_port),
        "--node.id",
        "steelsearch-release-load-node",
        "--node.name",
        "steelsearch-release-load-node",
        "--node.roles",
        "cluster_manager,data,ingest,remote_cluster_client",
        "--cluster.name",
        "steelsearch-release-load",
        "--path.data",
        str(work_dir / "data"),
    ]


def build_opensearch_command(root: Path, work_dir: Path, http_port: int, transport_port: int) -> list[str]:
    return [
        "bash",
        str(root / "tools/run-opensearch-dev.sh"),
    ]


def build_comparison_command(
    *,
    root: Path,
    output: Path,
    steel_http: int,
    open_http: int,
    duration_seconds: float,
    clients: int,
    corpus_size: int,
    vector_dimension: int,
    query_mix: str,
) -> list[str]:
    return [
        sys.executable,
        str(root / "tools/run-http-load-comparison.py"),
        "--steelsearch-url",
        f"http://127.0.0.1:{steel_http}",
        "--opensearch-url",
        f"http://127.0.0.1:{open_http}",
        "--index",
        "steelsearch-release-load-comparison",
        "--clients",
        str(clients),
        "--expected-node-count",
        "1",
        "--number-of-shards",
        "1",
        "--number-of-replicas",
        "0",
        "--corpus-size",
        str(corpus_size),
        "--vector-dimension",
        str(vector_dimension),
        "--duration-seconds",
        str(duration_seconds),
        "--query-mix",
        query_mix,
        "--timeout-seconds",
        "10",
        "--output",
        str(output),
    ]


def wait_for_health(http_port: int, *, timeout_seconds: float) -> None:
    url = f"http://127.0.0.1:{http_port}/_cluster/health"
    deadline = time.time() + timeout_seconds
    last_error = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as response:
                json.loads(response.read().decode("utf-8"))
            return
        except Exception as error:  # noqa: BLE001
            last_error = str(error)
            time.sleep(1)
    raise RuntimeError(f"endpoint did not become healthy: {last_error}")


def clear_opensearch_cluster_blocks(http_port: int, *, timeout_seconds: float) -> None:
    request_json(
        http_port,
        "/_cluster/settings",
        timeout_seconds=timeout_seconds,
        method="PUT",
        payload={
            "persistent": {
                "cluster.blocks.create_index": False,
                "cluster.routing.allocation.disk.threshold_enabled": False,
            },
            "transient": {
                "cluster.blocks.create_index": False,
                "cluster.routing.allocation.disk.threshold_enabled": False,
            },
        },
    )


def request_json(
    http_port: int,
    path: str,
    *,
    timeout_seconds: float,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"http://127.0.0.1:{http_port}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def terminate(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=10.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10.0)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_failed_output(output: Path, message: str, *, stderr_tail: str = "") -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": {
            "passed": False,
            "error_count": 1,
        },
        "targets": {},
        "comparison": {"mode": "failed"},
        "errors": [message],
        "stderr_tail": stderr_tail,
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def persist_summary(
    output: Path,
    report: dict[str, Any],
    *,
    returncode: int = 0,
    stderr_tail: str = "",
) -> dict[str, Any]:
    targets = report.get("targets")
    comparison = report.get("comparison")
    errors = []
    if not isinstance(targets, dict):
        errors.append("targets missing")
    else:
        for name in ("steelsearch", "opensearch"):
            target = targets.get(name)
            if not isinstance(target, dict) or target.get("returncode") != 0:
                errors.append(f"{name} returncode is not zero")
    if not isinstance(comparison, dict) or comparison.get("mode") != "completed":
        errors.append("comparison mode is not completed")
    if returncode != 0:
        errors.append(f"load comparison command returncode={returncode}")
    report["summary"] = {
        "passed": not errors,
        "error_count": len(errors),
        "command_returncode": returncode,
        "target_count": len(targets) if isinstance(targets, dict) else 0,
    }
    if errors:
        report["errors"] = errors
    if stderr_tail:
        report["stderr_tail"] = stderr_tail
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    sys.exit(main())
