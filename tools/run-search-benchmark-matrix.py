#!/usr/bin/env python3
"""Run 1-node and 3-node search + k-NN benchmark scenarios and write JSON/Markdown reports."""

from __future__ import annotations

import argparse
import json
import os
import signal
import shutil
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
DEFAULT_PROFILE = "minilm-knn"
PROFILES = {
    "minilm-knn": {
        "corpus_size": 5000,
        "vector_dimension": 384,
        "duration_seconds": 30.0,
        "clients": 4,
        "query_mix": "write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10,vector=15,hybrid=10,refresh=5",
    },
    "quick-minilm-knn": {
        "corpus_size": 1500,
        "vector_dimension": 384,
        "duration_seconds": 8.0,
        "clients": 4,
        "query_mix": "write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10,vector=15,hybrid=10,refresh=5",
    },
}


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
    def __init__(
        self,
        scenario: Scenario,
        process: subprocess.Popen[str],
        base_url: str,
        manifest_path: Path | None,
        log_dir: Path,
        container_names: list[str] | None = None,
        operation_log_path: Path | None = None,
    ) -> None:
        self.scenario = scenario
        self.process = process
        self.base_url = base_url
        self.manifest_path = manifest_path
        self.log_dir = log_dir
        self.container_names = container_names or []
        self.operation_log_path = operation_log_path

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
    parser.add_argument("--profile", choices=sorted(PROFILES), default=DEFAULT_PROFILE)
    parser.add_argument("--output-dir", default=str(ROOT / "target" / "search-benchmark-matrix"))
    parser.add_argument(
        "--scenarios",
        default=",".join(scenario.key for scenario in SCENARIOS),
        help="comma-separated scenario keys to run; use one or more of: "
        + ", ".join(scenario.key for scenario in SCENARIOS),
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="reuse an existing per-scenario baseline.json instead of rerunning that scenario",
    )
    parser.add_argument(
        "--aggregate-only",
        action="store_true",
        help="only aggregate existing per-scenario baseline.json files into summary/report",
    )
    parser.add_argument("--corpus-size", type=positive_int)
    parser.add_argument("--vector-dimension", type=positive_int)
    parser.add_argument("--duration-seconds", type=positive_float)
    parser.add_argument("--clients", type=positive_int)
    parser.add_argument("--number-of-shards", type=positive_int, default=3)
    parser.add_argument("--number-of-replicas", type=non_negative_int, default=1)
    parser.add_argument("--timeout-seconds", type=positive_float, default=10.0)
    parser.add_argument("--query-mix")
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument(
        "--operation-resource-deltas",
        action="store_true",
        help=(
            "ask the load runner to sample native telemetry counters before and after each operation; "
            "use --clients 1 for exact per-operation materialization attribution"
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    profile = PROFILES[args.profile]
    if args.corpus_size is None:
        args.corpus_size = profile["corpus_size"]
    if args.vector_dimension is None:
        args.vector_dimension = profile["vector_dimension"]
    if args.duration_seconds is None:
        args.duration_seconds = profile["duration_seconds"]
    if args.clients is None:
        args.clients = profile["clients"]
    if args.query_mix is None:
        args.query_mix = profile["query_mix"]
    try:
        scenarios = selected_scenarios(args.scenarios)
    except argparse.ArgumentTypeError as error:
        parser.error(str(error))

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
            "profile": args.profile,
            "operation_resource_deltas": args.operation_resource_deltas,
        },
        "scenarios": [
            {
                "key": scenario.key,
                "label": scenario.label,
                "engine": scenario.engine,
                "topology": scenario.topology,
                "node_count": scenario.node_count,
            }
            for scenario in scenarios
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
        "scenario_plan": plan["scenarios"],
        "scenarios": {},
    }
    handles: list[ClusterHandle] = []
    try:
        for scenario in scenarios:
            scenario_dir = output_dir / scenario.key
            baseline_output = scenario_dir / "baseline.json"
            if args.aggregate_only or (args.skip_existing and baseline_output.exists()):
                if not baseline_output.exists():
                    raise RuntimeError(f"{scenario.label} baseline does not exist: {baseline_output}")
                result = json.loads(baseline_output.read_text(encoding="utf-8"))
                result["base_url"] = result.get("base_url")
                result["manifest_path"] = result.get("manifest_path")
                results["scenarios"][scenario.key] = result
                continue
            if args.aggregate_only:
                continue
            if scenario_dir.exists():
                shutil.rmtree(scenario_dir)
            scenario_dir.mkdir(parents=True, exist_ok=True)
            handle = start_cluster(scenario, scenario_dir)
            handles.append(handle)
            wait_for_cluster(scenario, handle.base_url, args.timeout_seconds)
            if scenario.engine == "opensearch":
                clear_opensearch_cluster_blocks(handle.base_url, args.timeout_seconds)
            resource_pids = resolve_resource_pids(handle)
            result = run_baseline(scenario, handle, baseline_output, args, resource_pids)
            result["base_url"] = handle.base_url
            result["manifest_path"] = str(handle.manifest_path) if handle.manifest_path else None
            result["resource_process_pids"] = resource_pids
            result["resource_container_names"] = handle.container_names
            baseline_output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            results["scenarios"][scenario.key] = result
            handle.stop()
            handles.pop()
    finally:
        for handle in reversed(handles):
            handle.stop()

    results["native_telemetry_budgets"] = build_native_telemetry_budgets(results["scenarios"])
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


def selected_scenarios(value: str) -> tuple[Scenario, ...]:
    by_key = {scenario.key: scenario for scenario in SCENARIOS}
    keys = [key.strip() for key in value.split(",") if key.strip()]
    if not keys:
        raise argparse.ArgumentTypeError("--scenarios must include at least one scenario key")
    unknown = [key for key in keys if key not in by_key]
    if unknown:
        raise argparse.ArgumentTypeError(
            "unknown scenario key(s): "
            + ", ".join(unknown)
            + "; valid keys: "
            + ", ".join(by_key)
        )
    deduped = []
    seen = set()
    for key in keys:
        if key not in seen:
            deduped.append(by_key[key])
            seen.add(key)
    return tuple(deduped)


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
        env["STEELSEARCH_RUSTUP_TOOLCHAIN"] = "nightly"
        process = subprocess.Popen([str(STEELSEARCH_SINGLE)], cwd=ROOT, env=env, stdout=stdout, stderr=stderr, text=True)
        base_url = wait_for_url_in_log(log_dir / "stderr.log", "Steelsearch access URL: ")
        return ClusterHandle(
            scenario,
            process,
            base_url,
            None,
            log_dir,
            operation_log_path=Path(env["STEELSEARCH_WORK_DIR"]) / "data",
        )

    if scenario.engine == "steelsearch":
        env["STEELSEARCH_CLUSTER_WORK_DIR"] = str(scenario_dir / "cluster")
        env["STEELSEARCH_NODE_COUNT"] = str(scenario.node_count)
        env["STEELSEARCH_HTTP_HOST"] = "127.0.0.1"
        env["STEELSEARCH_TRANSPORT_HOST"] = "127.0.0.1"
        env["STEELSEARCH_BUILD_PROFILE"] = "release"
        env["STEELSEARCH_RUSTUP_TOOLCHAIN"] = "nightly"
        process = subprocess.Popen([str(STEELSEARCH_CLUSTER)], cwd=ROOT, env=env, stdout=stdout, stderr=stderr, text=True)
        manifest_path = Path(env["STEELSEARCH_CLUSTER_WORK_DIR"]) / "cluster.json"
        base_url = wait_for_manifest_url(manifest_path)
        return ClusterHandle(
            scenario,
            process,
            base_url,
            manifest_path,
            log_dir,
            operation_log_path=Path(env["STEELSEARCH_CLUSTER_WORK_DIR"]),
        )

    if scenario.engine == "opensearch" and scenario.node_count == 1:
        env["OPENSEARCH_HTTP_HOST"] = "127.0.0.1"
        env["OPENSEARCH_HTTP_PORT"] = str(free_port())
        env["OPENSEARCH_VECTOR_CONTAINER_NAME"] = f"steelsearch-bench-opensearch-single-{int(time.time())}"
        process = subprocess.Popen([str(OPENSEARCH_SINGLE)], cwd=ROOT, env=env, stdout=stdout, stderr=stderr, text=True)
        base_url = f"http://127.0.0.1:{env['OPENSEARCH_HTTP_PORT']}"
        return ClusterHandle(
            scenario,
            process,
            base_url,
            None,
            log_dir,
            container_names=[env["OPENSEARCH_VECTOR_CONTAINER_NAME"]],
        )

    env["OPENSEARCH_CLUSTER_WORK_DIR"] = str(scenario_dir / "cluster")
    env["OPENSEARCH_NODE_COUNT"] = str(scenario.node_count)
    env["OPENSEARCH_HTTP_HOST"] = "127.0.0.1"
    env["OPENSEARCH_CLUSTER_NAME"] = f"bench-{scenario.key}"
    unique_suffix = f"{scenario.key}-{int(time.time())}"
    env["OPENSEARCH_CLUSTER_CONTAINER_PREFIX"] = f"steelsearch-bench-{unique_suffix}"
    env["OPENSEARCH_CLUSTER_NETWORK_NAME"] = f"steelsearch-bench-{unique_suffix}-net"
    process = subprocess.Popen([str(OPENSEARCH_CLUSTER)], cwd=ROOT, env=env, stdout=stdout, stderr=stderr, text=True)
    manifest_path = Path(env["OPENSEARCH_CLUSTER_WORK_DIR"]) / "cluster.json"
    base_url = wait_for_manifest_url(manifest_path)
    container_names = [
        f"{env['OPENSEARCH_CLUSTER_CONTAINER_PREFIX']}-{index}"
        for index in range(1, scenario.node_count + 1)
    ]
    return ClusterHandle(scenario, process, base_url, manifest_path, log_dir, container_names=container_names)


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
    health_url = f"{base_url}/_cluster/health"
    while time.time() < deadline:
        try:
            payload = http_json(health_url, timeout_seconds)
            if isinstance(payload, dict) and int(payload.get("number_of_nodes", 0)) >= scenario.node_count:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"{scenario.label} did not reach {scenario.node_count} nodes")


def clear_opensearch_cluster_blocks(base_url: str, timeout_seconds: float) -> None:
    payload = {
        "persistent": {
            "cluster.blocks.create_index": False,
            "cluster.routing.allocation.disk.threshold_enabled": False,
        },
        "transient": {
            "cluster.blocks.create_index": False,
            "cluster.routing.allocation.disk.threshold_enabled": False,
        },
    }
    http_json(
        f"{base_url}/_cluster/settings",
        timeout_seconds,
        method="PUT",
        payload=payload,
    )


def resolve_resource_pids(handle: ClusterHandle) -> list[int]:
    if handle.container_names:
        return docker_container_pids(handle.container_names)
    return steelsearch_resource_pids(handle.process.pid)


def docker_container_pids(container_names: list[str]) -> list[int]:
    pids: list[int] = []
    for container_name in container_names:
        completed = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Pid}}", container_name],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            continue
        try:
            pid = int(completed.stdout.strip())
        except ValueError:
            continue
        if pid > 0:
            pids.append(pid)
    return dedupe_ints(pids)


def steelsearch_resource_pids(root_pid: int) -> list[int]:
    candidates = [root_pid, *descendant_pids(root_pid)]
    steelsearch_pids = [
        pid for pid in candidates
        if process_cmdline(pid) and Path(process_cmdline(pid)[0]).name == "steelsearch"
    ]
    if steelsearch_pids:
        return dedupe_ints(steelsearch_pids)
    return dedupe_ints([pid for pid in candidates if Path(f"/proc/{pid}/status").exists()])


def descendant_pids(root_pid: int) -> list[int]:
    children_by_parent: dict[int, list[int]] = {}
    for stat_path in Path("/proc").glob("[0-9]*/stat"):
        try:
            text = stat_path.read_text(encoding="utf-8")
            right = text.rsplit(") ", 1)[1]
            fields = right.split()
            parent_pid = int(fields[1])
            pid = int(stat_path.parent.name)
        except (IndexError, OSError, ValueError):
            continue
        children_by_parent.setdefault(parent_pid, []).append(pid)

    descendants: list[int] = []
    stack = list(children_by_parent.get(root_pid, []))
    while stack:
        pid = stack.pop()
        descendants.append(pid)
        stack.extend(children_by_parent.get(pid, []))
    return descendants


def process_cmdline(pid: int) -> list[str]:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return []
    return [part.decode("utf-8", errors="replace") for part in raw.split(b"\0") if part]


def dedupe_ints(values: list[int]) -> list[int]:
    deduped: list[int] = []
    seen = set()
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped


def run_baseline(
    scenario: Scenario,
    handle: ClusterHandle,
    output_path: Path,
    args: argparse.Namespace,
    resource_pids: list[int],
) -> dict[str, Any]:
    replicas = 0 if scenario.node_count == 1 else min(args.number_of_replicas, scenario.node_count - 1)
    command = [
        sys.executable,
        str(BASELINE),
        "--base-url",
        handle.base_url,
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
    if resource_pids:
        command.extend(["--process-pids", ",".join(str(pid) for pid in resource_pids)])
    if handle.operation_log_path is not None:
        command.extend(["--operation-log-path", str(handle.operation_log_path)])
    if args.operation_resource_deltas:
        command.append("--operation-resource-deltas")
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, env=os.environ.copy(), check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"{scenario.label} baseline failed: {completed.stderr.strip() or completed.stdout.strip()}")
    return json.loads(output_path.read_text(encoding="utf-8"))


def http_json(
    url: str,
    timeout_seconds: float,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, method=method, headers=headers, data=data)
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
            "resource_usage": compare_resource_usage(
                steel.get("resource_usage", {}),
                open_.get("resource_usage", {}),
            ),
            "operations": {
                operation: {
                    "throughput_ops_per_second": compare_number(
                        operation_throughput_ops_per_second(steel, operation),
                        operation_throughput_ops_per_second(open_, operation),
                    ),
                    "p50_ms": compare_number(
                        steel["operations"][operation]["latency_ms"].get("p50"),
                        open_["operations"][operation]["latency_ms"].get("p50"),
                    ),
                    "p95_ms": compare_number(
                        steel["operations"][operation]["latency_ms"].get("p95"),
                        open_["operations"][operation]["latency_ms"].get("p95"),
                    ),
                    "p99_ms": compare_number(
                        steel["operations"][operation]["latency_ms"].get("p99"),
                        open_["operations"][operation]["latency_ms"].get("p99"),
                    ),
                    "mean_ms": compare_number(
                        steel["operations"][operation]["latency_ms"].get("mean"),
                        open_["operations"][operation]["latency_ms"].get("mean"),
                    ),
                }
                for operation in sorted(set(steel["operations"]) & set(open_["operations"]))
            },
        }
        comparisons[topology]["steelsearch_slower_than_opensearch"] = slower_than_opensearch(
            comparisons[topology]
        )
    return comparisons


def operation_throughput_ops_per_second(
    scenario_result: dict[str, Any],
    operation: str,
) -> float | None:
    elapsed = scenario_result.get("summary", {}).get("elapsed_seconds")
    success_count = scenario_result.get("operations", {}).get(operation, {}).get("success_count")
    if not isinstance(elapsed, (int, float)) or elapsed <= 0:
        return None
    if not isinstance(success_count, (int, float)):
        return None
    return success_count / elapsed


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


def compare_resource_usage(steel_usage: dict[str, Any], open_usage: dict[str, Any]) -> dict[str, Any]:
    compared: dict[str, Any] = {}
    for key in sorted(set(steel_usage) | set(open_usage)):
        steel_metric = steel_usage.get(key, {})
        open_metric = open_usage.get(key, {})
        compared[key] = {
            sample: compare_number(
                steel_metric.get(sample) if isinstance(steel_metric, dict) else None,
                open_metric.get(sample) if isinstance(open_metric, dict) else None,
            )
            for sample in ("before", "after", "delta", "peak")
        }
    return compared


MATERIALIZATION_BUDGETS = {
    "materialized_response_fetches": {
        "max_per_success": 1.0,
        "description": "total materialized response fetches per successful operation",
    },
    "compatibility_materialized_response_fetches": {
        "max_per_success": 1.0,
        "description": "compatibility materialized response fetches per successful operation",
    },
}


def build_native_telemetry_budgets(scenarios: dict[str, Any]) -> dict[str, Any]:
    budgets: dict[str, Any] = {}
    for scenario_key, payload in sorted(scenarios.items()):
        if not scenario_key.startswith("steelsearch-"):
            continue
        success_count = sum(
            operation.get("success_count", 0)
            for operation in payload.get("operations", {}).values()
            if isinstance(operation.get("success_count", 0), (int, float))
        )
        counters: dict[str, Any] = {}
        for counter, budget in MATERIALIZATION_BUDGETS.items():
            delta = payload.get("resource_usage", {}).get(counter, {}).get("delta")
            counters[counter] = materialization_budget_payload(delta, success_count, budget)
        operations: dict[str, Any] = {}
        for operation, op_payload in sorted(payload.get("operations", {}).items()):
            op_resource_usage = op_payload.get("resource_usage")
            if not isinstance(op_resource_usage, dict):
                continue
            op_success_count = op_payload.get("success_count", 0)
            operation_counters = {
                counter: materialization_budget_payload(
                    op_resource_usage.get(counter, {}).get("delta"),
                    op_success_count,
                    budget,
                )
                for counter, budget in MATERIALIZATION_BUDGETS.items()
            }
            operations[operation] = {
                "success_count": op_success_count,
                "counters": operation_counters,
                "status": aggregate_budget_status(operation_counters),
            }
        budgets[scenario_key] = {
            "success_count": success_count,
            "counters": counters,
            "operations": operations,
            "status": aggregate_budget_status(counters),
        }
    return budgets


def materialization_budget_payload(delta: Any, success_count: Any, budget: dict[str, Any]) -> dict[str, Any]:
    per_success = None
    status = "unknown"
    if isinstance(delta, (int, float)) and isinstance(success_count, (int, float)) and success_count > 0:
        per_success = delta / success_count
        status = "pass" if per_success <= budget["max_per_success"] else "fail"
    return {
        "delta": delta,
        "success_count": success_count,
        "per_success": per_success,
        "max_per_success": budget["max_per_success"],
        "status": status,
        "description": budget["description"],
    }


def aggregate_budget_status(counters: dict[str, Any]) -> str:
    statuses = {payload.get("status") for payload in counters.values()}
    if "fail" in statuses:
        return "fail"
    if "unknown" in statuses:
        return "unknown"
    return "pass"


def slower_than_opensearch(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    slower: list[dict[str, Any]] = []
    throughput = comparison["throughput_ops_per_second"]
    if isinstance(throughput.get("ratio"), (int, float)) and throughput["ratio"] < 1.0:
        slower.append(
            {
                "operation": "overall",
                "metric": "throughput_ops_per_second",
                "steelsearch": throughput["steelsearch"],
                "opensearch": throughput["opensearch"],
                "ratio": throughput["ratio"],
                "direction": "lower_is_worse",
            }
        )
    for operation, operation_comparison in comparison["operations"].items():
        throughput = operation_comparison["throughput_ops_per_second"]
        if isinstance(throughput.get("ratio"), (int, float)) and throughput["ratio"] < 1.0:
            slower.append(
                {
                    "operation": operation,
                    "metric": "throughput_ops_per_second",
                    "steelsearch": throughput["steelsearch"],
                    "opensearch": throughput["opensearch"],
                    "ratio": throughput["ratio"],
                    "direction": "lower_is_worse",
                }
            )
        for metric in ("p50_ms", "p95_ms", "p99_ms", "mean_ms"):
            values = operation_comparison[metric]
            if isinstance(values.get("ratio"), (int, float)) and values["ratio"] > 1.0:
                slower.append(
                    {
                        "operation": operation,
                        "metric": metric,
                        "steelsearch": values["steelsearch"],
                        "opensearch": values["opensearch"],
                        "ratio": values["ratio"],
                        "direction": "higher_is_worse",
                    }
                )
    return slower


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

    native_telemetry_budgets = results.get("native_telemetry_budgets")
    if not isinstance(native_telemetry_budgets, dict):
        native_telemetry_budgets = build_native_telemetry_budgets(results.get("scenarios", {}))

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
        "| Scenario | Throughput ops/s | Error rate | RSS peak MiB |",
        "| --- | ---: | ---: | ---: |",
    ]
    for scenario in SCENARIOS:
        payload = results["scenarios"].get(scenario.key)
        if not payload:
            continue
        rss_peak = (
            payload.get("resource_usage", {})
            .get("memory_rss_bytes", {})
            .get("peak")
        )
        lines.append(
            f"| {scenario.label} | {payload['summary']['throughput_ops_per_second']:.2f} | {payload['summary']['error_rate']:.4f} | {safe_mib(rss_peak)} |"
        )

    for scenario in SCENARIOS:
        payload = results["scenarios"].get(scenario.key)
        if not payload:
            continue
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
        if scenario.engine == "steelsearch":
            native_budget = native_telemetry_budgets.get(scenario.key, {})
            lines.extend(
                [
                    "",
                    "### Steelsearch native-path telemetry",
                    "",
                    "| Counter | Delta | After |",
                    "| --- | ---: | ---: |",
                ]
            )
            for counter in STEELSEARCH_NATIVE_TELEMETRY_COUNTERS:
                metric = payload.get("resource_usage", {}).get(counter, {})
                lines.append(
                    f"| `{counter}` | {safe_number(metric.get('delta'))} | {safe_number(metric.get('after'))} |"
                )
            lines.extend(
                [
                    "",
                    "### Steelsearch materialization budget",
                    "",
                    f"- Budget status: `{native_budget.get('status', 'unknown')}`",
                    "",
                    "| Counter | Delta | Successful ops | Per successful op | Max per successful op | Status |",
                    "| --- | ---: | ---: | ---: | ---: | --- |",
                ]
            )
            for counter, budget in native_budget.get("counters", {}).items():
                lines.append(
                    f"| `{counter}` | {safe_number(budget.get('delta'))} | {safe_number(budget.get('success_count'))} | {safe_number(budget.get('per_success'))} | {safe_number(budget.get('max_per_success'))} | `{budget.get('status', 'unknown')}` |"
                )
            if native_budget.get("operations"):
                lines.extend(
                    [
                        "",
                        "### Steelsearch operation materialization budget",
                        "",
                        "| Operation | Counter | Delta | Successful ops | Per successful op | Max per successful op | Status |",
                        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
                    ]
                )
                for operation, operation_budget in native_budget.get("operations", {}).items():
                    for counter, budget in operation_budget.get("counters", {}).items():
                        lines.append(
                            f"| {operation} | `{counter}` | {safe_number(budget.get('delta'))} | {safe_number(budget.get('success_count'))} | {safe_number(budget.get('per_success'))} | {safe_number(budget.get('max_per_success'))} | `{budget.get('status', 'unknown')}` |"
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
                f"- RSS peak ratio (Steelsearch/OpenSearch): `{safe_ratio(payload.get('resource_usage', {}).get('memory_rss_bytes', {}).get('peak', {}).get('ratio'))}`",
                "",
                "| Operation | Steelsearch ops/s | OpenSearch ops/s | Throughput ratio |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for operation, op_payload in payload["operations"].items():
            throughput = op_payload["throughput_ops_per_second"]
            lines.append(
                f"| {operation} | {safe_number(throughput['steelsearch'])} | {safe_number(throughput['opensearch'])} | {safe_ratio(throughput['ratio'])} |"
            )
        lines.extend(
            [
                "",
                "| Operation | Steelsearch p50 ms | OpenSearch p50 ms | Steelsearch p95 ms | OpenSearch p95 ms | Steelsearch p99 ms | OpenSearch p99 ms | Steelsearch mean ms | OpenSearch mean ms |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for operation, op_payload in payload["operations"].items():
            lines.append(
                f"| {operation} | {safe_number(op_payload['p50_ms']['steelsearch'])} | {safe_number(op_payload['p50_ms']['opensearch'])} | {safe_number(op_payload['p95_ms']['steelsearch'])} | {safe_number(op_payload['p95_ms']['opensearch'])} | {safe_number(op_payload['p99_ms']['steelsearch'])} | {safe_number(op_payload['p99_ms']['opensearch'])} | {safe_number(op_payload['mean_ms']['steelsearch'])} | {safe_number(op_payload['mean_ms']['opensearch'])} |"
            )
        lines.append("")
        slower = payload.get("steelsearch_slower_than_opensearch", [])
        if slower:
            lines.extend(
                [
                    "#### Steelsearch slower than OpenSearch",
                    "",
                    "| Operation | Metric | Steelsearch | OpenSearch | Ratio |",
                    "| --- | --- | ---: | ---: | ---: |",
                ]
            )
            for item in slower:
                lines.append(
                    f"| {item['operation']} | {item['metric']} | {safe_number(item['steelsearch'])} | {safe_number(item['opensearch'])} | {safe_ratio(item['ratio'])} |"
                )
            lines.append("")
        else:
            lines.extend(["#### Steelsearch slower than OpenSearch", "", "No slower metrics recorded for this topology.", ""])

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
            "- `fallback_query_string`: opt-in diagnostic query-string fallback case for materialization attribution.",
            "",
        ]
    )
    return "\n".join(lines)


STEELSEARCH_NATIVE_TELEMETRY_COUNTERS = (
    "materialized_response_fetches",
    "materialized_response_avoided_fetches",
    "compatibility_materialized_response_fetches",
    "request_result_cache_hybrid_vector_bypasses",
    "request_result_cache_unsupported_vector_bypasses",
    "request_result_cache_highlight_bypasses",
    "request_result_cache_explain_bypasses",
)


def safe_number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    if value is None:
        return "n/a"
    return str(value)


def safe_mib(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value / (1024 * 1024):.2f}"
    return "n/a"


def safe_ratio(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}x"
    return "n/a"


if __name__ == "__main__":
    sys.exit(main())
