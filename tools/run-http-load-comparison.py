#!/usr/bin/env python3
"""Compare Steelsearch and OpenSearch HTTP load baselines on one fixture."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tools" / "run-http-load-baseline.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steelsearch-url", default=os.environ.get("STEELSEARCH_URL"))
    parser.add_argument("--opensearch-url", default=os.environ.get("OPENSEARCH_URL"))
    parser.add_argument("--index", default="steelsearch-load-comparison")
    parser.add_argument("--clients", type=positive_int, default=4)
    parser.add_argument("--expected-node-count", type=positive_int, default=1)
    parser.add_argument("--number-of-shards", type=positive_int, default=1)
    parser.add_argument("--number-of-replicas", type=non_negative_int, default=0)
    parser.add_argument("--corpus-size", type=positive_int, default=256)
    parser.add_argument("--vector-dimension", type=positive_int, default=8)
    parser.add_argument("--duration-seconds", type=positive_float, default=30.0)
    parser.add_argument("--query-mix", default="write=20,lexical=30,vector=20,hybrid=20,refresh=10")
    parser.add_argument("--timeout-seconds", type=positive_float, default=10.0)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--output", help="write comparison JSON to this path")
    parser.add_argument("--dry-run", action="store_true", help="validate comparison configuration only")
    parser.add_argument("--no-reset", action="store_true", help="reuse existing indices")
    parser.add_argument("--metrics-path", default="/_nodes/stats")
    parser.add_argument("--steelsearch-process-pid", type=positive_int)
    parser.add_argument("--opensearch-process-pid", type=positive_int)
    parser.add_argument("--steelsearch-operation-log-path")
    parser.add_argument("--opensearch-operation-log-path")
    args = parser.parse_args()

    load_opt_in = (
        os.environ.get("RUN_HTTP_LOAD_COMPARISON") == "1"
        or os.environ.get("RUN_HTTP_LOAD_TESTS") == "1"
    )
    if not args.dry_run and not load_opt_in:
        print(
            "HTTP load comparison is long-running; set RUN_HTTP_LOAD_COMPARISON=1 or RUN_HTTP_LOAD_TESTS=1 to run it",
            file=sys.stderr,
        )
        return 2

    if not args.steelsearch_url:
        print("STEELSEARCH_URL or --steelsearch-url is required", file=sys.stderr)
        return 2
    if not args.opensearch_url:
        print("OPENSEARCH_URL or --opensearch-url is required", file=sys.stderr)
        return 2

    common = [
        "--index",
        args.index,
        "--clients",
        str(args.clients),
        "--expected-node-count",
        str(args.expected_node_count),
        "--number-of-shards",
        str(args.number_of_shards),
        "--number-of-replicas",
        str(args.number_of_replicas),
        "--corpus-size",
        str(args.corpus_size),
        "--vector-dimension",
        str(args.vector_dimension),
        "--duration-seconds",
        str(args.duration_seconds),
        "--query-mix",
        args.query_mix,
        "--timeout-seconds",
        str(args.timeout_seconds),
        "--seed",
        str(args.seed),
        "--metrics-path",
        args.metrics_path,
    ]
    if args.no_reset:
        common.append("--no-reset")
    if args.dry_run:
        common.append("--dry-run")

    steelsearch = run_baseline(
        "steelsearch",
        args.steelsearch_url,
        common,
        resource_args(args.steelsearch_process_pid, args.steelsearch_operation_log_path),
    )
    opensearch = run_baseline(
        "opensearch",
        args.opensearch_url,
        common,
        resource_args(args.opensearch_process_pid, args.opensearch_operation_log_path),
    )
    report = {
        "fixture": {
            "index": args.index,
            "clients": args.clients,
            "expected_node_count": args.expected_node_count,
            "number_of_shards": args.number_of_shards,
            "number_of_replicas": args.number_of_replicas,
            "corpus_size": args.corpus_size,
            "vector_dimension": args.vector_dimension,
            "duration_seconds": args.duration_seconds,
            "query_mix": args.query_mix,
            "seed": args.seed,
            "reset": not args.no_reset,
        },
        "targets": {
            "steelsearch": steelsearch,
            "opensearch": opensearch,
        },
        "comparison": compare(steelsearch, opensearch),
    }

    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")

    if args.dry_run:
        return 0
    failures = steelsearch["returncode"] != 0 or opensearch["returncode"] != 0
    return 1 if failures else 0


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be zero or greater")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def resource_args(process_pid: int | None, operation_log_path: str | None) -> list[str]:
    args: list[str] = []
    if process_pid is not None:
        args.extend(["--process-pid", str(process_pid)])
    if operation_log_path:
        args.extend(["--operation-log-path", operation_log_path])
    return args


def run_baseline(name: str, base_url: str, common: list[str], resources: list[str]) -> dict[str, Any]:
    command = [
        sys.executable,
        str(BASELINE),
        "--base-url",
        base_url.rstrip("/"),
        *common,
        *resources,
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    parsed: dict[str, Any]
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        parsed = {"parse_error": completed.stdout}
    return {
        "name": name,
        "base_url": base_url.rstrip("/"),
        "returncode": completed.returncode,
        "stdout": parsed,
        "stderr": completed.stderr.strip(),
    }


def compare(steelsearch: dict[str, Any], opensearch: dict[str, Any]) -> dict[str, Any]:
    steel = steelsearch.get("stdout", {})
    open_ = opensearch.get("stdout", {})
    if steel.get("dry_run") or open_.get("dry_run"):
        return {"mode": "dry-run", "comparable": True}

    steel_summary = steel.get("summary", {})
    open_summary = open_.get("summary", {})
    return {
        "mode": "completed",
        "throughput_ops_per_second": compare_number(
            steel_summary.get("throughput_ops_per_second"),
            open_summary.get("throughput_ops_per_second"),
        ),
        "error_rate": compare_number(error_rate(steel_summary), error_rate(open_summary)),
        "resource_usage": compare_resource_usage(
            steel.get("resource_usage", {}),
            open_.get("resource_usage", {}),
        ),
        "operations": compare_operations(steel.get("operations", {}), open_.get("operations", {})),
    }


def compare_resource_usage(steel_usage: dict[str, Any], open_usage: dict[str, Any]) -> dict[str, Any]:
    compared: dict[str, Any] = {}
    for metric in sorted(set(steel_usage) | set(open_usage)):
        steel_metric = steel_usage.get(metric, {})
        open_metric = open_usage.get(metric, {})
        compared[metric] = {
            key: compare_number(steel_metric.get(key), open_metric.get(key))
            for key in ("before", "after", "delta")
        }
    return compared


def compare_operations(steel_ops: dict[str, Any], open_ops: dict[str, Any]) -> dict[str, Any]:
    compared: dict[str, Any] = {}
    for operation in sorted(set(steel_ops) & set(open_ops)):
        steel_latency = steel_ops[operation].get("latency_ms", {})
        open_latency = open_ops[operation].get("latency_ms", {})
        compared[operation] = {
            "success_count": compare_number(
                steel_ops[operation].get("success_count"),
                open_ops[operation].get("success_count"),
            ),
            "error_count": compare_number(
                steel_ops[operation].get("error_count"),
                open_ops[operation].get("error_count"),
            ),
            "latency_ms": {
                key: compare_number(steel_latency.get(key), open_latency.get(key))
                for key in ("p50", "p90", "p95", "p99", "mean")
                if key in steel_latency and key in open_latency
            },
        }
    return compared


def error_rate(summary: dict[str, Any]) -> float | None:
    operations = summary.get("operation_count")
    errors = summary.get("error_count")
    if not isinstance(operations, (int, float)) or not isinstance(errors, (int, float)) or operations <= 0:
        return None
    return errors / operations


def compare_number(steel_value: Any, open_value: Any) -> dict[str, Any]:
    result = {"steelsearch": steel_value, "opensearch": open_value}
    if isinstance(steel_value, (int, float)) and isinstance(open_value, (int, float)):
        result["delta"] = steel_value - open_value
        result["ratio"] = steel_value / open_value if open_value else None
    return result


if __name__ == "__main__":
    sys.exit(main())
