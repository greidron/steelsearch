#!/usr/bin/env python3
"""Generate Steelsearch HTTP load evidence for release readiness."""

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
DEFAULT_OUTPUT = ROOT / "target/release-load-current/http-load-baseline.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--binary", type=Path, default=ROOT / "target/release/steelsearch")
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--duration-seconds", type=float, default=30.0)
    parser.add_argument("--clients", type=int, default=4)
    parser.add_argument("--corpus-size", type=int, default=256)
    parser.add_argument("--vector-dimension", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = generate_report(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.dry_run:
        return 0
    return 0 if report.get("summary", {}).get("error_count") == 0 else 1


def generate_report(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    binary = args.binary if args.binary.is_absolute() else root / args.binary
    work_dir = args.work_dir or Path(tempfile.mkdtemp(prefix="steelsearch-load.", dir=str(root / "target")))
    http_port = free_port("127.0.0.1")
    transport_port = free_port("127.0.0.1")
    load_command = build_load_command(
        root=root,
        output=args.output,
        http_port=http_port,
        duration_seconds=args.duration_seconds,
        clients=args.clients,
        corpus_size=args.corpus_size,
        vector_dimension=args.vector_dimension,
        process_pid="<steelsearch-pid>",
        log_dir=work_dir / "logs",
    )
    server_command = build_server_command(
        binary=binary,
        work_dir=work_dir,
        http_port=http_port,
        transport_port=transport_port,
    )
    if args.dry_run:
        return {
            "dry_run": True,
            "server_command": [str(part) for part in server_command],
            "load_command": [str(part) for part in load_command],
            "output": str(args.output),
            "work_dir": str(work_dir),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not binary.is_file():
        write_failed_output(args.output, f"steelsearch binary is missing: {binary}")
        return load_json(args.output)

    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "logs").mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["STEELSEARCH_DATA_PATH"] = str(work_dir / "data")
    env["STEELSEARCH_LOG_PATH"] = str(work_dir / "logs")
    server_log = work_dir / "steelsearch-load-server.log"
    with server_log.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            server_command,
            cwd=root,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
    try:
        wait_for_health(http_port, timeout_seconds=60.0)
        load_command = build_load_command(
            root=root,
            output=args.output,
            http_port=http_port,
            duration_seconds=args.duration_seconds,
            clients=args.clients,
            corpus_size=args.corpus_size,
            vector_dimension=args.vector_dimension,
            process_pid=str(process.pid),
            log_dir=work_dir / "logs",
        )
        completed = subprocess.run(
            load_command,
            cwd=root,
            env={**env, "RUN_HTTP_LOAD_TESTS": "1"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            write_failed_output(
                args.output,
                f"load baseline failed: returncode={completed.returncode}",
                stderr_tail=completed.stderr[-4000:],
            )
        report = load_json(args.output)
        return persist_passed_summary(args.output, report)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10.0)


def build_server_command(binary: Path, work_dir: Path, http_port: int, transport_port: int) -> list[str]:
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


def build_load_command(
    *,
    root: Path,
    output: Path,
    http_port: int,
    duration_seconds: float,
    clients: int,
    corpus_size: int,
    vector_dimension: int,
    process_pid: str,
    log_dir: Path,
) -> list[str]:
    return [
        sys.executable,
        str(root / "tools/run-http-load-baseline.py"),
        "--base-url",
        f"http://127.0.0.1:{http_port}",
        "--index",
        "steelsearch-release-load-current",
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
        "--timeout-seconds",
        "10",
        "--process-pid",
        process_pid,
        "--operation-log-path",
        str(log_dir),
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
        except Exception as error:  # noqa: BLE001 - surfaced in failure report
            last_error = str(error)
            time.sleep(1)
    raise RuntimeError(f"Steelsearch did not become healthy: {last_error}")


def free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


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
            "operation_count": 0,
            "success_count": 0,
            "error_rate": 1.0,
        },
        "errors": [message],
        "stderr_tail": stderr_tail,
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def persist_passed_summary(output: Path, report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary")
    if isinstance(summary, dict):
        summary["passed"] = summary.get("error_count") == 0
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    sys.exit(main())
