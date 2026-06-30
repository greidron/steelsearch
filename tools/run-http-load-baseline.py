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


DEFAULT_QUERY_MIX = "write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10,vector=15,hybrid=10,refresh=5"
OPERATIONS = (
    "write",
    "lexical",
    "ranking",
    "facet",
    "sort_filter",
    "nested",
    "vector",
    "hybrid",
    "refresh",
    "fallback_query_string",
    "fallback_terms_set",
    "fallback_distance_feature",
    "fallback_rank_feature",
    "fallback_more_like_this",
    "fallback_case_insensitive_wildcard",
)
NATIVE_TELEMETRY_COUNTERS = (
    "materialized_response_fetches",
    "materialized_response_avoided_fetches",
    "compatibility_materialized_response_fetches",
    "request_result_cache_hybrid_vector_bypasses",
    "request_result_cache_unsupported_vector_bypasses",
    "request_result_cache_highlight_bypasses",
    "request_result_cache_explain_bypasses",
)


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
    parser.add_argument(
        "--process-pids",
        help="comma-separated daemon PIDs; VmRSS is sampled as the sum across live PIDs",
    )
    parser.add_argument("--operation-log-path", help="sample operation-log file or directory size before and after the run")
    parser.add_argument(
        "--metrics-path",
        default="/_nodes/stats",
        help="HTTP metrics path used to sample vector cache counters when supported",
    )
    parser.add_argument(
        "--operation-resource-deltas",
        action="store_true",
        help=(
            "sample native telemetry counters before and after each operation; "
            "use clients=1 for exact per-operation attribution"
        ),
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
        "operation_resource_deltas": args.operation_resource_deltas,
    }

    if args.dry_run:
        emit(
            {
                "dry_run": True,
                "config": config,
                "operations": planned_operations(query_mix),
                "resource_usage": {
                    "memory_rss_bytes": {
                        "source": resource_pid_source(args.process_pid, args.process_pids),
                    },
                    "operation_log_bytes": {
                        "source": args.operation_log_path,
                    },
                    "vector_cache_bytes": {
                        "source": args.metrics_path,
                    },
                    **{counter: {"source": args.metrics_path} for counter in NATIVE_TELEMETRY_COUNTERS},
                },
            },
            args.output,
        )
        return 0

    runner = LoadRunner(config, args.timeout_seconds)
    probes = ResourceProbes(
        base_url=config["base_url"],
        timeout=args.timeout_seconds,
        process_pids=parse_process_pids(args.process_pid, args.process_pids),
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


def parse_process_pids(process_pid: int | None, process_pids: str | None) -> list[int]:
    pids: list[int] = []
    if process_pid is not None:
        pids.append(process_pid)
    if process_pids:
        for raw in process_pids.split(","):
            raw = raw.strip()
            if not raw:
                continue
            parsed = int(raw)
            if parsed <= 0:
                raise argparse.ArgumentTypeError("--process-pids values must be greater than zero")
            pids.append(parsed)
    deduped: list[int] = []
    seen = set()
    for pid in pids:
        if pid not in seen:
            deduped.append(pid)
            seen.add(pid)
    return deduped


def resource_pid_source(process_pid: int | None, process_pids: str | None) -> str | None:
    pids = parse_process_pids(process_pid, process_pids)
    if not pids:
        return None
    return ",".join(f"/proc/{pid}/status" for pid in pids)


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
        self.operation_resource_deltas: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def run(self, probes: "ResourceProbes") -> dict[str, Any]:
        before = probes.sample()
        self.prepare_index()
        self.seed_corpus()

        probes.start_peak_sampling()
        start = time.monotonic()
        deadline = start + self.config["duration_seconds"]
        threads = [
            threading.Thread(target=self.worker, args=(client_id, deadline, probes), daemon=True)
            for client_id in range(self.config["clients"])
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        elapsed = time.monotonic() - start

        total_success = sum(self.success.values())
        total_errors = sum(self.errors.values())
        peak = probes.stop_peak_sampling()
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
            "resource_usage": compare_resource_samples(before, after, peak),
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

        vector_enabled = (
            self.config["query_mix"].get("vector", 0) > 0
            or self.config["query_mix"].get("hybrid", 0) > 0
        )
        fallback_diagnostics_enabled = fallback_diagnostic_operations_enabled(self.config["query_mix"])
        settings = {
            "index": {
                "number_of_shards": self.config["number_of_shards"],
                "number_of_replicas": self.config["number_of_replicas"],
            }
        }
        if vector_enabled:
            settings["index"]["knn"] = True
        properties = {
            "title": {"type": "text"},
            "message": {"type": "text"},
            "category": {"type": "keyword"},
            "service": {"type": "keyword"},
            "tenant": {"type": "keyword"},
            "status": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "events": {
                "type": "nested",
                "properties": {
                    "kind": {"type": "keyword"},
                    "status": {"type": "keyword"},
                },
            },
            "price": {"type": "double"},
            "latency": {"type": "long"},
            "event_time": {"type": "date"},
        }
        if fallback_diagnostics_enabled:
            properties["signal"] = {"type": "float"}
            properties["fallback_shape"] = {"type": "geo_point"}
            properties["fallback_priority"] = {"type": "keyword"}
        if vector_enabled:
            properties["embedding"] = {
                "type": "knn_vector",
                "dimension": self.config["vector_dimension"],
            }
        body = {
            "settings": {
                **settings,
            },
            "mappings": {
                "properties": properties,
            },
        }
        response = self.http("PUT", f"/{index}", body)
        if response["status"] not in (200, 201, 400):
            raise RuntimeError(f"failed to create {index}: {response}")
        if response["status"] == 400 and "resource_already_exists" not in json.dumps(response.get("body", {})):
            raise RuntimeError(f"failed to create {index}: {response}")

    def seed_corpus(self) -> None:
        fallback_diagnostics_enabled = fallback_diagnostic_operations_enabled(self.config["query_mix"])
        for doc_id in range(self.config["corpus_size"]):
            response = self.index_document(
                f"seed-{doc_id}",
                document_for(
                    doc_id,
                    self.config["vector_dimension"],
                    fallback_diagnostics_enabled=fallback_diagnostics_enabled,
                ),
            )
            if response["status"] not in (200, 201):
                raise RuntimeError(f"failed to seed document {doc_id}: {response}")
        response = self.http("POST", f"/{self.config['index']}/_refresh", {})
        if response["status"] >= 300:
            raise RuntimeError(f"failed to refresh seed corpus: {response}")

    def worker(self, client_id: int, deadline: float, probes: "ResourceProbes") -> None:
        rng = random.Random(self.config["seed"] + client_id)
        cumulative = cumulative_weights(self.config["query_mix"])
        counter = 0
        while time.monotonic() < deadline:
            operation = choose_operation(rng, cumulative)
            counter += 1
            before_operation = self.operation_resource_sample(probes)
            started = time.perf_counter()
            try:
                response = self.run_operation(operation, client_id, counter, rng)
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                after_operation = self.operation_resource_sample(probes)
                self.record_operation_resource_delta(operation, before_operation, after_operation)
                self.record(operation, elapsed_ms, response)
            except Exception as error:  # noqa: BLE001 - report load-test failures per operation
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                after_operation = self.operation_resource_sample(probes)
                self.record_operation_resource_delta(operation, before_operation, after_operation)
                self.record_exception(operation, elapsed_ms, error)

    def run_operation(self, operation: str, client_id: int, counter: int, rng: random.Random) -> dict[str, Any]:
        if operation == "write":
            doc_id = self.config["corpus_size"] + client_id * 1_000_000 + counter
            return self.index_document(
                f"live-{client_id}-{counter}",
                document_for(
                    doc_id,
                    self.config["vector_dimension"],
                    fallback_diagnostics_enabled=self.config["query_mix"].get("fallback_query_string", 0) > 0,
                ),
            )
        if operation == "lexical":
            return self.search(
                {
                    "size": 10,
                    "query": {
                        "bool": {
                            "must": [{"match": {"message": rng.choice(["alpha", "bravo", "checkout", "premium"])}}],
                            "filter": [
                                {"term": {"tenant": rng.choice(["tenant-a", "tenant-b"])}},
                                {"term": {"status": rng.choice(["ok", "warn"])}},
                            ],
                        }
                    },
                }
            )
        if operation == "ranking":
            return self.search(
                {
                    "size": 10,
                    "query": {
                        "bool": {
                            "must": [
                                {
                                    "multi_match": {
                                        "query": rng.choice(["premium checkout", "fast catalog", "vector search", "analytics dashboard"]),
                                        "fields": ["title^2", "message"],
                                        "type": "best_fields",
                                    }
                                }
                            ],
                            "should": [
                                {"match_phrase": {"message": {"query": rng.choice(["premium checkout", "fast catalog"]), "slop": 1}}},
                                {"term": {"service": rng.choice(["checkout", "catalog", "payments", "search"])}} ,
                            ],
                            "minimum_should_match": 1,
                            "filter": [{"range": {"latency": {"lte": rng.choice([250, 400, 600])}}}],
                        }
                    },
                }
            )
        if operation == "facet":
            return self.search(
                {
                    "size": 0,
                    "query": {
                        "bool": {
                            "must": [{"match": {"message": rng.choice(["service", "search", "event", "analytics"])}}],
                            "filter": [{"term": {"tenant": rng.choice(["tenant-a", "tenant-b"])}}],
                        }
                    },
                    "aggs": {
                        "by_service": {"terms": {"field": "service", "size": 8}},
                        "by_category": {"terms": {"field": "category", "size": 8}},
                        "latency_ranges": {
                            "range": {
                                "field": "latency",
                                "ranges": [{"to": 100}, {"from": 100, "to": 300}, {"from": 300}],
                            }
                        },
                        "recent_events": {
                            "date_histogram": {
                                "field": "event_time",
                                "calendar_interval": "day",
                            }
                        },
                    },
                }
            )
        if operation == "sort_filter":
            return self.search(
                {
                    "size": 10,
                    "query": {
                        "bool": {
                            "filter": [
                                {"term": {"tenant": rng.choice(["tenant-a", "tenant-b"])}},
                                {"term": {"category": rng.choice(["commerce", "search", "analytics"])}} ,
                                {"range": {"price": {"gte": 10.0, "lte": rng.choice([50.0, 75.0, 100.0])}}},
                            ],
                            "must": [{"match": {"message": rng.choice(["service", "catalog", "checkout"])}}],
                        }
                    },
                    "sort": [{"latency": "asc"}, {"price": "desc"}],
                }
            )
        if operation == "nested":
            return self.search(
                {
                    "size": 10,
                    "query": {
                        "nested": {
                            "path": "events",
                            "query": {
                                "bool": {
                                    "must": [
                                        {"term": {"events.kind": rng.choice(["payment", "cache"])}},
                                        {"term": {"events.status": rng.choice(["timeout", "accepted"])}},
                                    ]
                                }
                            },
                        }
                    },
                }
            )
        if operation == "vector":
            doc_id = rng.randrange(self.config["corpus_size"])
            return self.search(
                {
                    "size": 10,
                    "query": {"knn": {"embedding": {"vector": vector_for(doc_id, self.config["vector_dimension"]), "k": 10}}},
                }
            )
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
        if operation == "fallback_query_string":
            return self.search(
                {
                    "size": 10,
                    "query": {
                        "query_string": {
                            "query": "api",
                            "fields": ["signal"],
                        }
                    },
                }
            )
        if operation == "fallback_terms_set":
            return self.search(
                {
                    "size": 10,
                    "query": {
                        "terms_set": {
                            "fallback_shape": {
                                "terms": ["alpha", "beta"],
                                "minimum_should_match": 2,
                            }
                        }
                    },
                }
            )
        if operation == "fallback_distance_feature":
            return self.search(
                {
                    "size": 10,
                    "query": {
                        "distance_feature": {
                            "field": "fallback_priority",
                            "origin": 0.0,
                            "pivot": 5.0,
                        }
                    },
                }
            )
        if operation == "fallback_rank_feature":
            return self.search(
                {
                    "size": 10,
                    "query": {
                        "rank_feature": {
                            "field": "fallback_priority",
                        }
                    },
                }
            )
        if operation == "fallback_more_like_this":
            return self.search(
                {
                    "size": 10,
                    "query": {
                        "more_like_this": {
                            "like": ["api"],
                        }
                    },
                }
            )
        if operation == "fallback_case_insensitive_wildcard":
            return self.search(
                {
                    "size": 10,
                    "query": {
                        "wildcard": {
                            "message": {
                                "value": "ALPHA*",
                                "case_insensitive": True,
                            }
                        }
                    },
                }
            )
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

    def operation_resource_sample(self, probes: "ResourceProbes") -> dict[str, int | None] | None:
        if not self.config.get("operation_resource_deltas"):
            return None
        return probes.native_counter_sample()

    def record_operation_resource_delta(
        self,
        operation: str,
        before: dict[str, int | None] | None,
        after: dict[str, int | None] | None,
    ) -> None:
        if before is None or after is None:
            return
        with self.lock:
            for counter in NATIVE_TELEMETRY_COUNTERS:
                value = delta(after.get(counter), before.get(counter))
                if value is not None and value > 0:
                    self.operation_resource_deltas[operation][counter] += value

    def operation_summary(self, operation: str) -> dict[str, Any]:
        samples = self.samples[operation]
        summary = {
            "success_count": self.success[operation],
            "error_count": self.errors[operation],
            "latency_ms": latency_summary(samples),
            "error_examples": self.error_examples[operation],
        }
        if self.config.get("operation_resource_deltas"):
            summary["resource_usage"] = {
                counter: {"delta": self.operation_resource_deltas[operation].get(counter, 0)}
                for counter in NATIVE_TELEMETRY_COUNTERS
            }
        return summary

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
        process_pids: list[int],
        operation_log_path: str | None,
        metrics_path: str,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.process_pids = process_pids
        self.operation_log_path = Path(operation_log_path) if operation_log_path else None
        self.metrics_path = metrics_path
        self._peak_memory_rss_bytes: int | None = None
        self._sampler_stop = threading.Event()
        self._sampler_thread: threading.Thread | None = None

    def sample(self) -> dict[str, Any]:
        metrics = self.http_metrics()
        return {
            "memory_rss_bytes": process_rss_bytes(self.process_pids),
            "operation_log_bytes": path_size(self.operation_log_path),
            "vector_cache_bytes": vector_cache_bytes(metrics),
            **{counter: metric_counter(metrics, counter) for counter in NATIVE_TELEMETRY_COUNTERS},
        }

    def native_counter_sample(self) -> dict[str, int | None]:
        metrics = self.http_metrics()
        return {counter: metric_counter(metrics, counter) for counter in NATIVE_TELEMETRY_COUNTERS}

    def start_peak_sampling(self, interval_seconds: float = 0.25) -> None:
        if not self.process_pids or self._sampler_thread is not None:
            return
        self._sampler_stop.clear()

        def run() -> None:
            while not self._sampler_stop.wait(interval_seconds):
                value = process_rss_bytes(self.process_pids)
                if value is not None:
                    if self._peak_memory_rss_bytes is None or value > self._peak_memory_rss_bytes:
                        self._peak_memory_rss_bytes = value

        self._sampler_thread = threading.Thread(target=run, daemon=True)
        self._sampler_thread.start()

    def stop_peak_sampling(self) -> dict[str, Any]:
        if self.process_pids:
            value = process_rss_bytes(self.process_pids)
            if value is not None:
                if self._peak_memory_rss_bytes is None or value > self._peak_memory_rss_bytes:
                    self._peak_memory_rss_bytes = value
        self._sampler_stop.set()
        if self._sampler_thread is not None:
            self._sampler_thread.join(timeout=2.0)
        return {"memory_rss_bytes": self._peak_memory_rss_bytes}

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


def process_rss_bytes(pids: list[int]) -> int | None:
    if not pids:
        return None
    values = [process_single_rss_bytes(pid) for pid in pids]
    live_values = [value for value in values if value is not None]
    if not live_values:
        return None
    return sum(live_values)


def process_single_rss_bytes(pid: int) -> int | None:
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


def metric_counter(metrics: Any, key: str) -> int | None:
    values = find_numeric_key(metrics, key)
    return sum(values) if values else None


def find_numeric_key(value: Any, target_key: str) -> list[int]:
    found: list[int] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == target_key and isinstance(child, (int, float)):
                found.append(int(child))
            else:
                found.extend(find_numeric_key(child, target_key))
    elif isinstance(value, list):
        for child in value:
            found.extend(find_numeric_key(child, target_key))
    return found


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


def compare_resource_samples(
    before: dict[str, Any],
    after: dict[str, Any],
    peak: dict[str, Any] | None = None,
) -> dict[str, Any]:
    peak = peak or {}
    return {
        key: {
            "before": before.get(key),
            "after": after.get(key),
            "delta": delta(after.get(key), before.get(key)),
            "peak": peak.get(key),
        }
        for key in (
            "memory_rss_bytes",
            "operation_log_bytes",
            "vector_cache_bytes",
            *NATIVE_TELEMETRY_COUNTERS,
        )
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


def fallback_diagnostic_operations_enabled(query_mix: dict[str, int]) -> bool:
    return any(
        query_mix.get(operation, 0) > 0
        for operation in (
            "fallback_query_string",
            "fallback_terms_set",
            "fallback_distance_feature",
            "fallback_rank_feature",
            "fallback_more_like_this",
            "fallback_case_insensitive_wildcard",
        )
    )


def document_for(doc_id: int, dimension: int, *, fallback_diagnostics_enabled: bool = False) -> dict[str, Any]:
    terms = ("alpha", "bravo", "charlie", "delta", "checkout", "catalog", "premium", "analytics")
    services = ("checkout", "catalog", "payments", "search")
    categories = ("commerce", "search", "analytics")
    statuses = ("ok", "warn", "error")
    day = (doc_id % 28) + 1
    service = services[doc_id % len(services)]
    category = categories[doc_id % len(categories)]
    document = {
        "title": f"{category} {service} summary {doc_id}",
        "message": f"{terms[doc_id % len(terms)]} service event {doc_id}",
        "category": category,
        "service": service,
        "tenant": ("tenant-a", "tenant-b")[doc_id % 2],
        "status": statuses[doc_id % len(statuses)],
        "tags": [service, category, terms[doc_id % len(terms)]],
        "events": [
            {
                "kind": "payment" if doc_id % 4 in (0, 1) else "cache",
                "status": "timeout" if doc_id % 4 == 0 else "accepted",
            },
            {
                "kind": "cache" if doc_id % 4 in (0, 2) else "payment",
                "status": "timeout" if doc_id % 4 == 1 else "accepted",
            },
        ],
        "price": round(5.0 + ((doc_id * 17) % 1000) / 10.0, 2),
        "latency": 10 + (doc_id * 37) % 900,
        "event_time": f"2026-01-{day:02d}T12:00:00Z",
        "embedding": vector_for(doc_id, dimension),
    }
    if fallback_diagnostics_enabled:
        document["signal"] = fallback_signal_for(doc_id)
        document["fallback_shape"] = fallback_shape_for(doc_id)
        document["fallback_priority"] = fallback_priority_for(doc_id)
    return document


def fallback_signal_for(doc_id: int) -> Any:
    match doc_id % 3:
        case 0:
            return "api"
        case 1:
            return "worker"
        case _:
            return ["api", "checkout"]


def fallback_shape_for(doc_id: int) -> list[str]:
    match doc_id % 3:
        case 0:
            return ["alpha", "beta"]
        case 1:
            return ["alpha", "gamma"]
        case _:
            return ["beta", "alpha", "omega"]


def fallback_priority_for(doc_id: int) -> Any:
    match doc_id % 4:
        case 0:
            return 2.0
        case 1:
            return 0.0
        case 2:
            return [3.0, "cold"]
        case _:
            return [False, True]


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
