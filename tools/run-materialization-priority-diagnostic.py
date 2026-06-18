#!/usr/bin/env python3
"""Run a fresh Steelsearch materialization diagnostic and rank fallback priorities."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", default="target/materialization-priority-diagnostic")
    parser.add_argument("--duration-seconds", type=float, default=3.0)
    parser.add_argument("--corpus-size", type=int, default=128)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    work_dir = Path(args.work_dir)
    baseline_path = work_dir / "load-baseline.json"
    priority_path = work_dir / "materialization-priority.json"
    markdown_path = work_dir / "materialization-priority.md"
    if args.dry_run:
        report = {
            "summary": {
                "passed": True,
                "dry_run": True,
                "baseline_path": str(baseline_path),
                "priority_path": str(priority_path),
                "markdown_path": str(markdown_path),
            }
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    if work_dir.exists():
        shutil.rmtree(work_dir)
    (work_dir / "node" / "data").mkdir(parents=True, exist_ok=True)
    (work_dir / "node" / "logs").mkdir(parents=True, exist_ok=True)

    binary = build_steelsearch()
    http_port = free_port()
    transport_port = free_port()
    process = subprocess.Popen(
        [
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
            "steel-materialization-priority-node",
            "--node.name",
            "steel-materialization-priority-node",
            "--cluster.name",
            "steel-materialization-priority",
            "--node.roles",
            "cluster_manager,data,ingest,remote_cluster_client",
            "--path.data",
            str(work_dir / "node" / "data"),
        ],
        cwd=ROOT,
        stdout=open(work_dir / "node" / "logs" / "stdout.log", "wb"),
        stderr=open(work_dir / "node" / "logs" / "stderr.log", "wb"),
    )
    base_url = f"http://127.0.0.1:{http_port}"
    try:
        wait_for_endpoint(base_url, args.timeout_seconds)
        env = os.environ.copy()
        env["RUN_HTTP_LOAD_TESTS"] = "1"
        subprocess.run(
            [
                "python3",
                "tools/run-http-load-baseline.py",
                "--base-url",
                base_url,
                "--index",
                "materialization-priority-diagnostic",
                "--clients",
                "1",
                "--expected-node-count",
                "1",
                "--number-of-shards",
                "1",
                "--number-of-replicas",
                "0",
                "--corpus-size",
                str(args.corpus_size),
                "--duration-seconds",
                str(args.duration_seconds),
                "--query-mix",
                "fallback_query_string=1",
                "--operation-resource-deltas",
                "--output",
                str(baseline_path),
            ],
            cwd=ROOT,
            env=env,
            check=True,
        )
        priority = subprocess.run(
            [
                "python3",
                "tools/rank-materialization-priorities.py",
                str(baseline_path),
                "--format",
                "json",
                "--allow-empty",
                "--output",
                str(priority_path),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if priority.returncode != 0:
            raise RuntimeError(priority.stdout)
        subprocess.run(
            [
                "python3",
                "tools/rank-materialization-priorities.py",
                str(baseline_path),
                "--format",
                "markdown",
                "--allow-empty",
                "--output",
                str(markdown_path),
            ],
            cwd=ROOT,
            check=True,
        )
        priority_payload = json.loads(priority_path.read_text(encoding="utf-8"))
        baseline_payload = json.loads(baseline_path.read_text(encoding="utf-8"))
        report = {
            "summary": {
                "passed": bool(priority_payload["summary"].get("passed"))
                and baseline_payload["summary"].get("error_count") == 0,
                "base_url": base_url,
                "baseline_path": str(baseline_path),
                "priority_path": str(priority_path),
                "markdown_path": str(markdown_path),
                "top_operation": priority_payload["summary"].get("top_operation"),
                "top_family": priority_payload["summary"].get("top_family"),
                "success_count": baseline_payload["summary"].get("success_count"),
                "error_count": baseline_payload["summary"].get("error_count"),
            },
            "priority_summary": priority_payload["summary"],
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["summary"]["passed"] else 1
    finally:
        terminate(process)


def build_steelsearch() -> Path:
    subprocess.run(
        ["cargo", "build", "-p", "os-node", "--features", "standalone-runtime", "--bin", "steelsearch"],
        cwd=ROOT,
        check=True,
    )
    return ROOT / "target" / "debug" / "steelsearch"


def wait_for_endpoint(base_url: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(base_url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception as error:  # noqa: BLE001 - startup readiness probe.
            last_error = error
        time.sleep(0.2)
    raise TimeoutError(f"{base_url} did not become ready; last error={last_error}")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def terminate(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
