#!/usr/bin/env python3
"""Run a sustained HTTP load baseline against Steelsearch or OpenSearch."""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any


DEFAULT_QUERY_MIX = "write=20,lexical=30,vector=20,hybrid=20,refresh=10"
OPERATIONS = ("write", "lexical", "vector", "hybrid", "refresh")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:9200")
    parser.add_argument("--index", default="steelsearch-load-baseline")
    parser.add_argument("--clients", type=positive_int, default=4)
    parser.add_argument("--expected-node-count", type=positive_int, default=1)
    parser.add_argument("--number-of-shards", type=positive_int, default=1)
    parser.add_argument("--number-of-replicas", type=non_negative_int, default=0)
    parser.add_argument("--corpus-size", type=positive_int, default=256)
    parser.add_argument("--vector-dimension", type=positive_int, default=8)
    parser.add_argument("--duration-seconds", type=positive_float, default=30.0)
    parser.add_argument("--query-mix", default=DEFAULT_QUERY_MIX)
    parser.add_argument("--timeout-seconds", type=positive_float, default=10.0)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--output", help="write JSON summary to this path")
    parser.add_argument("--dry-run", action="store_true", help="validate configuration without issuing HTTP requests")
    parser.add_argument("--no-reset", action="store_true", help="reuse an existing index instead of deleting it first")
    parser.add_argument("--process-pid", type=positive_int, help="sample daemon VmRSS from /proc/<pid>/status")
    parser.add_argument("--operation-log-path", help="sample operation-log file or directory size before and after the run")
    parser.add_argument(
        "--metrics-path",
        default="/_nodes/stats",
        help="HTTP metrics path used to sample vector cache counters when supported",
    )
    args = parser.parse_args()

    load_opt_in = os.environ.get("RUN_HTTP_LOAD_TESTS") == "1" or os.environ.get("RUN_HTTP_LOAD_COMPARISON") == "1"
    if not args.dry_run and not load_opt_in:
        print(
            "HTTP load tests are long-running; set RUN_HTTP_LOAD_TESTS=1 or RUN_HTTP_LOAD_COMPARISON=1 to run them",
            file=sys.stderr,
        )
        return 2

    try:
        query_mix = parse_query_mix(args.query_mix)
    except argparse.ArgumentTypeError as error:
        parser.error(str(error))
    config = {
        "base_url": args.base_url.rstrip("/"),
        "index": args.index,
        "clients": args.clients,
        "expected_node_count": args.expected_node_count,
        "number_of_shards": args.number_of_shards,
        "number_of_replicas": args.number_of_replicas,
        "corpus_size": args.corpus_size,
        "vector_dimension": args.vector_dimension,
        "duration_seconds": args.duration_seconds,
        "query_mix": query_mix,
        "seed": args.seed,
        "reset": not args.no_reset,
    }

    if args.dry_run:
        emit(
            {
                "dry_run": True,
                "config": config,
                "operations": planned_operations(query_mix),
                "resource_usage": {
                    "memory_rss_bytes": {
                        "source": f"/proc/{args.process_pid}/status" if args.process_pid else None,
                    },
                    "operation_log_bytes": {
                        "source": args.operation_log_path,
                    },
                    "vector_cache_bytes": {
                        "source": args.metrics_path,
                    },
                },
            },
            args.output,
        )
        return 0

    runner = LoadRunner(config, args.timeout_seconds)
    probes = ResourceProbes(
        base_url=config["base_url"],
        timeout=args.timeout_seconds,
        process_pid=args.process_pid,
        operation_log_path=args.operation_log_path,
        metrics_path=args.metrics_path,
    )
    summary = runner.run(probes)
    emit(summary, args.output)
    return 1 if summary["summary"]["error_count"] else 0


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


def parse_query_mix(value: str) -> dict[str, int]:
    weights: dict[str, int] = {}
    for part in value.split(","):
        item = part.strip()
        if not item:
            continue
        if "=" not in item:
            raise argparse.ArgumentTypeError(f"query mix item must be name=weight: {item}")
        name, raw_weight = item.split("=", 1)
        name = name.strip()
        if name not in OPERATIONS:
            raise argparse.ArgumentTypeError(f"unsupported operation in query mix: {name}")
        weight = int(raw_weight)
        if weight < 0:
            raise argparse.ArgumentTypeError(f"query mix weight must be non-negative: {item}")
        weights[name] = weight
    if not weights or sum(weights.values()) <= 0:
        raise argparse.ArgumentTypeError("query mix must contain at least one positive weight")
    return {operation: weights.get(operation, 0) for operation in OPERATIONS}


def planned_operations(query_mix: dict[str, int]) -> list[dict[str, Any]]:
    total = sum(query_mix.values())
    return [
        {"operation": operation, "weight": weight, "share": weight / total}
        for operation, weight in query_mix.items()
        if weight > 0
    ]


class LoadRunner:
    def __init__(self, config: dict[str, Any], timeout: float) -> None:
        self.config = config
        self.timeout = timeout
        self.lock = threading.Lock()
        self.samples: dict[str, list[float]] = defaultdict(list)
        self.success: dict[str, int] = defaultdict(int)
        self.errors: dict[str, int] = defaultdict(int)
        self.error_examples: dict[str, list[str]] = defaultdict(list)

    def run(self, probes: "ResourceProbes") -> dict[str, Any]:
        before = probes.sample()
        self.prepare_index()
        self.seed_corpus()

        start = time.monotonic()
        deadline = start + self.config["duration_seconds"]
        threads = [
            threading.Thread(target=self.worker, args=(client_id, deadline), daemon=True)
            for client_id in range(self.config["clients"])
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        elapsed = time.monotonic() - start

        total_success = sum(self.success.values())
        total_errors = sum(self.errors.values())
        after = probes.sample()
        return {
            "config": self.config,
            "summary": {
                "elapsed_seconds": elapsed,
                "operation_count": total_success + total_errors,
                "success_count": total_success,
                "error_count": total_errors,
                "error_rate": total_errors / (total_success + total_errors) if total_success + total_errors else 0.0,
                "throughput_ops_per_second": total_success / elapsed if elapsed else 0.0,
            },
            "resource_usage": compare_resource_samples(before, after),
            "operations": {
                operation: self.operation_summary(operation)
                for operation in OPERATIONS
                if self.success[operation] or self.errors[operation]
            },
        }

    def prepare_index(self) -> None:
        index = self.config["index"]
        if self.config["reset"]:
            response = self.http("DELETE", f"/{index}")
            if response["status"] not in (200, 202, 404):
                raise RuntimeError(f"failed to delete {index}: {response}")

        body = {
            "settings": {
                "index": {
                    "knn": True,
                    "number_of_shards": self.config["number_of_shards"],
                    "number_of_replicas": self.config["number_of_replicas"],
                }
            },
            "mappings": {
                "properties": {
                    "message": {"type": "text"},
                    "service": {"type": "keyword"},
                    "tenant": {"type": "keyword"},
                    "latency": {"type": "long"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": self.config["vector_dimension"],
                    },
                }
            },
        }
        response = self.http("PUT", f"/{index}", body)
        if response["status"] not in (200, 201, 400):
            raise RuntimeError(f"failed to create {index}: {response}")
        if response["status"] == 400 and "resource_already_exists" not in json.dumps(response.get("body", {})):
            raise RuntimeError(f"failed to create {index}: {response}")

    def seed_corpus(self) -> None:
        for doc_id in range(self.config["corpus_size"]):
            response = self.index_document(f"seed-{doc_id}", document_for(doc_id, self.config["vector_dimension"]))
            if response["status"] not in (200, 201):
                raise RuntimeError(f"failed to seed document {doc_id}: {response}")
        response = self.http("POST", f"/{self.config['index']}/_refresh", {})
        if response["status"] >= 300:
            raise RuntimeError(f"failed to refresh seed corpus: {response}")

    def worker(self, client_id: int, deadline: float) -> None:
        rng = random.Random(self.config["seed"] + client_id)
        cumulative = cumulative_weights(self.config["query_mix"])
        counter = 0
        while time.monotonic() < deadline:
            operation = choose_operation(rng, cumulative)
            counter += 1
            started = time.perf_counter()
            try:
                response = self.run_operation(operation, client_id, counter, rng)
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                self.record(operation, elapsed_ms, response)
            except Exception as error:  # noqa: BLE001 - report load-test failures per operation
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                self.record_exception(operation, elapsed_ms, error)

    def run_operation(self, operation: str, client_id: int, counter: int, rng: random.Random) -> dict[str, Any]:
        if operation == "write":
            doc_id = self.config["corpus_size"] + client_id * 1_000_000 + counter
            return self.index_document(f"live-{client_id}-{counter}", document_for(doc_id, self.config["vector_dimension"]))
        if operation == "lexical":
            return self.search({"size": 10, "query": {"match": {"message": rng.choice(["alpha", "bravo", "checkout"])}}})
        if operation == "vector":
            doc_id = rng.randrange(self.config["corpus_size"])
            return self.search({"size": 10, "query": {"knn": {"embedding": {"vector": vector_for(doc_id, self.config["vector_dimension"]), "k": 10}}}})
        if operation == "hybrid":
            doc_id = rng.randrange(self.config["corpus_size"])
            return self.search(
                {
                    "size": 10,
                    "query": {
                        "bool": {
                            "must": [
                                {"match": {"message": "alpha"}},
                                {"knn": {"embedding": {"vector": vector_for(doc_id, self.config["vector_dimension"]), "k": 10}}},
                            ],
                            "filter": [{"term": {"tenant": "tenant-a"}}],
                        }
                    },
                }
            )
        if operation == "refresh":
            return self.http("POST", f"/{self.config['index']}/_refresh", {})
        raise RuntimeError(f"unsupported operation: {operation}")

    def index_document(self, doc_id: str, document: dict[str, Any]) -> dict[str, Any]:
        encoded_id = urllib.parse.quote(doc_id, safe="")
        return self.http("PUT", f"/{self.config['index']}/_doc/{encoded_id}?refresh=false", document)

    def search(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.http("POST", f"/{self.config['index']}/_search", body)

    def record(self, operation: str, elapsed_ms: float, response: dict[str, Any]) -> None:
        with self.lock:
            self.samples[operation].append(elapsed_ms)
            if 200 <= response["status"] < 300:
                self.success[operation] += 1
            else:
                self.errors[operation] += 1
                if len(self.error_examples[operation]) < 3:
                    self.error_examples[operation].append(json.dumps(response, sort_keys=True)[:500])

    def record_exception(self, operation: str, elapsed_ms: float, error: Exception) -> None:
        with self.lock:
            self.samples[operation].append(elapsed_ms)
            self.errors[operation] += 1
            if len(self.error_examples[operation]) < 3:
                self.error_examples[operation].append(repr(error))

    def operation_summary(self, operation: str) -> dict[str, Any]:
        samples = self.samples[operation]
        return {
            "success_count": self.success[operation],
            "error_count": self.errors[operation],
            "latency_ms": latency_summary(samples),
            "error_examples": self.error_examples[operation],
        }

    def http(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.config['base_url']}{path}"
        data = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = response.read()
                return {"status": response.status, "body": decode_body(payload)}
        except urllib.error.HTTPError as error:
            return {"status": error.code, "body": decode_body(error.read())}


class ResourceProbes:
    def __init__(
        self,
        base_url: str,
        timeout: float,
        process_pid: int | None,
        operation_log_path: str | None,
        metrics_path: str,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.process_pid = process_pid
        self.operation_log_path = Path(operation_log_path) if operation_log_path else None
        self.metrics_path = metrics_path

    def sample(self) -> dict[str, Any]:
        metrics = self.http_metrics()
        return {
            "memory_rss_bytes": process_rss_bytes(self.process_pid),
            "operation_log_bytes": path_size(self.operation_log_path),
            "vector_cache_bytes": vector_cache_bytes(metrics),
        }

    def http_metrics(self) -> Any:
        if not self.metrics_path:
            return None
        request = urllib.request.Request(
            self.base_url + self.metrics_path,
            method="GET",
            headers={"Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return decode_body(response.read())
        except Exception:  # noqa: BLE001 - metrics endpoints are optional across targets
            return None


def process_rss_bytes(pid: int | None) -> int | None:
    if pid is None:
        return None
    status = Path(f"/proc/{pid}/status")
    try:
        for line in status.read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                parts = line.split()
                if len(parts) >= 2:
                    return int(parts[1]) * 1024
    except OSError:
        return None
    return None


def path_size(path: Path | None) -> int | None:
    if path is None or not path.exists():
        return None
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total


def vector_cache_bytes(metrics: Any) -> int | None:
    values = find_numeric_metrics(metrics, ("cache",), ("bytes", "size", "memory", "used"))
    values.extend(find_numeric_metrics(metrics, ("native", "memory"), ("bytes", "size", "used")))
    return sum(values) if values else None


def find_numeric_metrics(value: Any, required_key_terms: tuple[str, ...], value_key_terms: tuple[str, ...]) -> list[int]:
    found: list[int] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_lower = key.lower()
            if (
                isinstance(child, (int, float))
                and all(term in key_lower for term in required_key_terms)
                and any(term in key_lower for term in value_key_terms)
            ):
                found.append(int(child))
            else:
                found.extend(find_numeric_metrics(child, required_key_terms, value_key_terms))
    elif isinstance(value, list):
        for child in value:
            found.extend(find_numeric_metrics(child, required_key_terms, value_key_terms))
    return found


def compare_resource_samples(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return {
        key: {
            "before": before.get(key),
            "after": after.get(key),
            "delta": delta(after.get(key), before.get(key)),
        }
        for key in ("memory_rss_bytes", "operation_log_bytes", "vector_cache_bytes")
    }


def delta(after: int | None, before: int | None) -> int | None:
    if after is None or before is None:
        return None
    return after - before


def cumulative_weights(query_mix: dict[str, int]) -> list[tuple[int, str]]:
    cumulative: list[tuple[int, str]] = []
    total = 0
    for operation, weight in query_mix.items():
        if weight <= 0:
            continue
        total += weight
        cumulative.append((total, operation))
    return cumulative


def choose_operation(rng: random.Random, cumulative: list[tuple[int, str]]) -> str:
    selected = rng.randint(1, cumulative[-1][0])
    for threshold, operation in cumulative:
        if selected <= threshold:
            return operation
    return cumulative[-1][1]


def document_for(doc_id: int, dimension: int) -> dict[str, Any]:
    terms = ("alpha", "bravo", "charlie", "delta", "checkout", "catalog")
    return {
        "message": f"{terms[doc_id % len(terms)]} service event {doc_id}",
        "service": ("checkout", "catalog", "payments", "search")[doc_id % 4],
        "tenant": ("tenant-a", "tenant-b")[doc_id % 2],
        "latency": 10 + (doc_id * 37) % 900,
        "embedding": vector_for(doc_id, dimension),
    }


def vector_for(doc_id: int, dimension: int) -> list[float]:
    return [round((((doc_id + 1) * 31 + offset * 17) % 1000) / 1000.0, 6) for offset in range(dimension)]


def latency_summary(samples: list[float]) -> dict[str, float | int]:
    if not samples:
        return {"count": 0}
    ordered = sorted(samples)
    return {
        "count": len(samples),
        "min": ordered[0],
        "p50": percentile(ordered, 50),
        "p90": percentile(ordered, 90),
        "p95": percentile(ordered, 95),
        "p99": percentile(ordered, 99),
        "max": ordered[-1],
        "mean": statistics.fmean(ordered),
    }


def percentile(ordered: list[float], percent: int) -> float:
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (percent / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def decode_body(payload: bytes) -> Any:
    if not payload:
        return {}
    try:
        return json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError:
        return payload.decode("utf-8", errors="replace")


def emit(summary: dict[str, Any], output: str | None) -> None:
    text = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(text)
    print(text, end="")


if __name__ == "__main__":
    sys.exit(main())
