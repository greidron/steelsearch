#!/usr/bin/env python3
"""Run 1-node and 3-node search + k-NN benchmark scenarios and write JSON/Markdown reports."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tools" / "run-http-load-baseline.py"
STEELSEARCH_SINGLE = ROOT / "tools" / "run-steelsearch-dev.sh"
STEELSEARCH_CLUSTER = ROOT / "tools" / "run-steelsearch-cluster-dev.sh"
OPENSEARCH_SINGLE = ROOT / "tools" / "run-opensearch-vector-dev.sh"
OPENSEARCH_CLUSTER = ROOT / "tools" / "run-opensearch-cluster-dev.sh"
DEFAULT_QUERY_MIX = "write=15,lexical=15,ranking=15,facet=15,sort_filter=10,vector=15,hybrid=10,refresh=5"


@dataclass(frozen=True)
class Scenario:
    engine: str
    topology: str
    node_count: int
    label: str

    @property
    def key(self) -> str:
        return f"{self.engine}-{self.topology}"


SCENARIOS = (
    Scenario("steelsearch", "single-node", 1, "Steelsearch 1-node"),
    Scenario("opensearch", "single-node", 1, "OpenSearch 1-node"),
    Scenario("steelsearch", "three-node", 3, "Steelsearch 3-node"),
    Scenario("opensearch", "three-node", 3, "OpenSearch 3-node"),
)


class ClusterHandle:
    def __init__(self, scenario: Scenario, process: subprocess.Popen[str], base_url: str, manifest_path: Path | None, log_dir: Path) -> None:
        self.scenario = scenario
        self.process = process
        self.base_url = base_url
        self.manifest_path = manifest_path
        self.log_dir = log_dir

    def stop(self) -> None:
        if self.process.poll() is not None:
            return
        self.process.send_signal(signal.SIGTERM)
        try:
            self.process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=10)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "target" / "search-benchmark-matrix"))
    parser.add_argument("--corpus-size", type=positive_int, default=5000)
    parser.add_argument("--vector-dimension", type=positive_int, default=16)
    parser.add_argument("--duration-seconds", type=positive_float, default=30.0)
    parser.add_argument("--clients", type=positive_int, default=4)
    parser.add_argument("--number-of-shards", type=positive_int, default=3)
    parser.add_argument("--number-of-replicas", type=non_negative_int, default=1)
    parser.add_argument("--timeout-seconds", type=positive_float, default=10.0)
    parser.add_argument("--query-mix", default=DEFAULT_QUERY_MIX)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    report_path = output_dir / "report.md"

    plan = {
        "generated_at_epoch_seconds": int(time.time()),
        "config": {
            "corpus_size": args.corpus_size,
            "vector_dimension": args.vector_dimension,
            "duration_seconds": args.duration_seconds,
            "clients": args.clients,
            "number_of_shards": args.number_of_shards,
            "number_of_replicas": args.number_of_replicas,
            "timeout_seconds": args.timeout_seconds,
            "query_mix": args.query_mix,
            "seed": args.seed,
        },
        "scenarios": [
            {
                "key": scenario.key,
                "label": scenario.label,
                "engine": scenario.engine,
                "topology": scenario.topology,
                "node_count": scenario.node_count,
            }
            for scenario in SCENARIOS
        ],
    }
    if args.dry_run:
        summary_path.write_text(json.dumps({"dry_run": True, **plan}, indent=2) + "\n", encoding="utf-8")
        report_path.write_text(render_report({"dry_run": True, **plan}), encoding="utf-8")
        print(json.dumps({"dry_run": True, **plan}, indent=2))
        return 0

    os.environ["RUN_HTTP_LOAD_TESTS"] = "1"
    results: dict[str, Any] = {
        "generated_at_epoch_seconds": int(time.time()),
        "config": plan["config"],
        "scenarios": {},
    }
    handles: list[ClusterHandle] = []
    try:
        for scenario in SCENARIOS:
            scenario_dir = output_dir / scenario.key
            scenario_dir.mkdir(parents=True, exist_ok=True)
            handle = start_cluster(scenario, scenario_dir)
            handles.append(handle)
            wait_for_cluster(scenario, handle.base_url, args.timeout_seconds)
            baseline_output = scenario_dir / "baseline.json"
            result = run_baseline(scenario, handle.base_url, baseline_output, args)
            result["base_url"] = handle.base_url
            result["manifest_path"] = str(handle.manifest_path) if handle.manifest_path else None
            results["scenarios"][scenario.key] = result
            handle.stop()
            handles.pop()
    finally:
        for handle in reversed(handles):
            handle.stop()

    results["comparisons"] = build_comparisons(results["scenarios"])
    summary_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(render_report(results), encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0


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


def start_cluster(scenario: Scenario, scenario_dir: Path) -> ClusterHandle:
    log_dir = scenario_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout = (log_dir / "stdout.log").open("w", encoding="utf-8")
    stderr = (log_dir / "stderr.log").open("w", encoding="utf-8")
    env = os.environ.copy()

    if scenario.engine == "steelsearch" and scenario.node_count == 1:
        env["STEELSEARCH_HTTP_HOST"] = "127.0.0.1"
        env["STEELSEARCH_TRANSPORT_HOST"] = "127.0.0.1"
        env["STEELSEARCH_WORK_DIR"] = str(scenario_dir / "node-1")
        env["STEELSEARCH_BUILD_PROFILE"] = "release"
        process = subprocess.Popen([str(STEELSEARCH_SINGLE)], cwd=ROOT, env=env, stdout=stdout, stderr=stderr, text=True)
        base_url = wait_for_url_in_log(log_dir / "stderr.log", "Steelsearch access URL: ")
        return ClusterHandle(scenario, process, base_url, None, log_dir)

    if scenario.engine == "steelsearch":
        env["STEELSEARCH_CLUSTER_WORK_DIR"] = str(scenario_dir / "cluster")
        env["STEELSEARCH_NODE_COUNT"] = str(scenario.node_count)
        env["STEELSEARCH_HTTP_HOST"] = "127.0.0.1"
        env["STEELSEARCH_TRANSPORT_HOST"] = "127.0.0.1"
        env["STEELSEARCH_BUILD_PROFILE"] = "release"
        process = subprocess.Popen([str(STEELSEARCH_CLUSTER)], cwd=ROOT, env=env, stdout=stdout, stderr=stderr, text=True)
        manifest_path = Path(env["STEELSEARCH_CLUSTER_WORK_DIR"]) / "cluster.json"
        base_url = wait_for_manifest_url(manifest_path)
        return ClusterHandle(scenario, process, base_url, manifest_path, log_dir)

    if scenario.engine == "opensearch" and scenario.node_count == 1:
        env["OPENSEARCH_HTTP_HOST"] = "127.0.0.1"
        env["OPENSEARCH_HTTP_PORT"] = str(free_port())
        env["OPENSEARCH_VECTOR_CONTAINER_NAME"] = f"steelsearch-bench-opensearch-single-{int(time.time())}"
        process = subprocess.Popen([str(OPENSEARCH_SINGLE)], cwd=ROOT, env=env, stdout=stdout, stderr=stderr, text=True)
        base_url = f"http://127.0.0.1:{env['OPENSEARCH_HTTP_PORT']}"
        return ClusterHandle(scenario, process, base_url, None, log_dir)

    env["OPENSEARCH_CLUSTER_WORK_DIR"] = str(scenario_dir / "cluster")
    env["OPENSEARCH_NODE_COUNT"] = str(scenario.node_count)
    env["OPENSEARCH_HTTP_HOST"] = "127.0.0.1"
    env["OPENSEARCH_CLUSTER_NAME"] = f"bench-{scenario.key}"
    process = subprocess.Popen([str(OPENSEARCH_CLUSTER)], cwd=ROOT, env=env, stdout=stdout, stderr=stderr, text=True)
    manifest_path = Path(env["OPENSEARCH_CLUSTER_WORK_DIR"]) / "cluster.json"
    base_url = wait_for_manifest_url(manifest_path)
    return ClusterHandle(scenario, process, base_url, manifest_path, log_dir)


def wait_for_url_in_log(log_path: Path, prefix: str, timeout: float = 120.0) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if log_path.exists():
            text = log_path.read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines():
                if line.startswith(prefix):
                    return line[len(prefix):].strip()
        time.sleep(0.25)
    raise RuntimeError(f"timed out waiting for {prefix!r} in {log_path}")


def wait_for_manifest_url(manifest_path: Path, timeout: float = 120.0) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            return manifest["nodes"][0]["http_url"]
        time.sleep(0.25)
    raise RuntimeError(f"timed out waiting for manifest at {manifest_path}")


def free_port(host: str = "127.0.0.1") -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def wait_for_cluster(scenario: Scenario, base_url: str, timeout_seconds: float) -> None:
    deadline = time.time() + 180.0
    health_url = f"{base_url}/_cluster/health?wait_for_nodes=>={scenario.node_count}&timeout=1s"
    while time.time() < deadline:
        try:
            payload = http_json(health_url, timeout_seconds)
            if isinstance(payload, dict) and int(payload.get("number_of_nodes", 0)) >= scenario.node_count:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"{scenario.label} did not reach {scenario.node_count} nodes")


def run_baseline(scenario: Scenario, base_url: str, output_path: Path, args: argparse.Namespace) -> dict[str, Any]:
    replicas = 0 if scenario.node_count == 1 else min(args.number_of_replicas, scenario.node_count - 1)
    command = [
        sys.executable,
        str(BASELINE),
        "--base-url",
        base_url,
        "--index",
        f"search-benchmark-{scenario.key}",
        "--clients",
        str(args.clients),
        "--expected-node-count",
        str(scenario.node_count),
        "--number-of-shards",
        str(args.number_of_shards),
        "--number-of-replicas",
        str(replicas),
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
        "--output",
        str(output_path),
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, env=os.environ.copy(), check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"{scenario.label} baseline failed: {completed.stderr.strip() or completed.stdout.strip()}")
    return json.loads(output_path.read_text(encoding="utf-8"))


def http_json(url: str, timeout_seconds: float) -> Any:
    request = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def build_comparisons(scenarios: dict[str, Any]) -> dict[str, Any]:
    comparisons: dict[str, Any] = {}
    for topology in ("single-node", "three-node"):
        steel = scenarios.get(f"steelsearch-{topology}")
        open_ = scenarios.get(f"opensearch-{topology}")
        if not steel or not open_:
            continue
        comparisons[topology] = {
            "throughput_ops_per_second": compare_number(
                steel["summary"]["throughput_ops_per_second"],
                open_["summary"]["throughput_ops_per_second"],
            ),
            "error_rate": compare_number(
                steel["summary"]["error_rate"],
                open_["summary"]["error_rate"],
            ),
            "operations": {
                operation: {
                    "p95_ms": compare_number(
                        steel["operations"][operation]["latency_ms"].get("p95"),
                        open_["operations"][operation]["latency_ms"].get("p95"),
                    ),
                    "p99_ms": compare_number(
                        steel["operations"][operation]["latency_ms"].get("p99"),
                        open_["operations"][operation]["latency_ms"].get("p99"),
                    ),
                }
                for operation in sorted(set(steel["operations"]) & set(open_["operations"]))
            },
        }
    return comparisons


def compare_number(steel_value: Any, open_value: Any) -> dict[str, Any]:
    delta = None
    ratio = None
    if isinstance(steel_value, (int, float)) and isinstance(open_value, (int, float)):
        delta = steel_value - open_value
        if open_value not in (0, 0.0):
            ratio = steel_value / open_value
    return {
        "steelsearch": steel_value,
        "opensearch": open_value,
        "delta": delta,
        "ratio": ratio,
    }


def render_report(results: dict[str, Any]) -> str:
    if results.get("dry_run"):
        return "\n".join(
            [
                "# Search and k-NN benchmark matrix",
                "",
                "Dry run only.",
                "",
                "## Planned scenarios",
                "",
                "| Scenario | Topology | Nodes |",
                "| --- | --- | ---: |",
                *[
                    f"| {scenario['label']} | {scenario['topology']} | {scenario['node_count']} |"
                    for scenario in results["scenarios"]
                ],
                "",
            ]
        )

    lines = [
        "# Search and k-NN benchmark report",
        "",
        "## Run configuration",
        "",
        f"- Generated at epoch seconds: `{results['generated_at_epoch_seconds']}`",
        f"- Corpus size: `{results['config']['corpus_size']}` documents",
        f"- Vector dimension: `{results['config']['vector_dimension']}`",
        f"- Duration per scenario: `{results['config']['duration_seconds']}` seconds",
        f"- Clients: `{results['config']['clients']}`",
        f"- Query mix: `{results['config']['query_mix']}`",
        "",
        "## Scenario summary",
        "",
        "| Scenario | Throughput ops/s | Error rate |",
        "| --- | ---: | ---: |",
    ]
    for scenario in SCENARIOS:
        payload = results["scenarios"][scenario.key]
        lines.append(
            f"| {scenario.label} | {payload['summary']['throughput_ops_per_second']:.2f} | {payload['summary']['error_rate']:.4f} |"
        )

    for scenario in SCENARIOS:
        payload = results["scenarios"][scenario.key]
        lines.extend(
            [
                "",
                f"## {scenario.label}",
                "",
                f"- Base URL: `{payload['base_url']}`",
                f"- Manifest: `{payload['manifest_path']}`" if payload.get("manifest_path") else "- Manifest: n/a",
                "",
                "| Operation | Success | Errors | p50 ms | p95 ms | p99 ms | Mean ms |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for operation, op_payload in payload["operations"].items():
            latency = op_payload["latency_ms"]
            lines.append(
                "| {operation} | {success_count} | {error_count} | {p50:.2f} | {p95:.2f} | {p99:.2f} | {mean:.2f} |".format(
                    operation=operation,
                    success_count=op_payload["success_count"],
                    error_count=op_payload["error_count"],
                    p50=latency.get("p50", 0.0),
                    p95=latency.get("p95", 0.0),
                    p99=latency.get("p99", 0.0),
                    mean=latency.get("mean", 0.0),
                )
            )

    lines.extend(
        [
            "",
            "## Steelsearch vs OpenSearch by topology",
            "",
        ]
    )
    for topology, payload in results.get("comparisons", {}).items():
        lines.extend(
            [
                f"### {topology}",
                "",
                f"- Throughput ratio (Steelsearch/OpenSearch): `{safe_ratio(payload['throughput_ops_per_second']['ratio'])}`",
                f"- Error rate delta (Steelsearch-OpenSearch): `{safe_number(payload['error_rate']['delta'])}`",
                "",
                "| Operation | Steelsearch p95 ms | OpenSearch p95 ms | Steelsearch p99 ms | OpenSearch p99 ms |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for operation, op_payload in payload["operations"].items():
            lines.append(
                f"| {operation} | {safe_number(op_payload['p95_ms']['steelsearch'])} | {safe_number(op_payload['p95_ms']['opensearch'])} | {safe_number(op_payload['p99_ms']['steelsearch'])} | {safe_number(op_payload['p99_ms']['opensearch'])} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Workload coverage",
            "",
            "- `lexical`: warmed match/term + filter search.",
            "- `ranking`: multi-match, phrase-sensitive ranking-oriented search.",
            "- `facet`: query + `terms`, `date_histogram`, and `range` aggregations.",
            "- `sort_filter`: filtered search with explicit sort keys.",
            "- `vector`: k-NN query against the vector field.",
            "- `hybrid`: lexical + k-NN + filter combined query.",
            "",
        ]
    )
    return "\n".join(lines)


def safe_number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    if value is None:
        return "n/a"
    return str(value)


def safe_ratio(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}x"
    return "n/a"


if __name__ == "__main__":
    sys.exit(main())
