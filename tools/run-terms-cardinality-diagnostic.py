#!/usr/bin/env python3
"""Compare owned single-node terms requests across cardinalities, not a release gate."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import time
import urllib.request

from run_core_performance_gate import file_hash


ROOT = Path(__file__).resolve().parents[1]
CARDINALITIES = (3, 8, 9, 32, 1024)
ORDER = ("before", "after", "after", "before")


def category_key(key, cardinality, pattern):
    if pattern == "benchmark" and cardinality == 3:
        return ("commerce", "search", "analytics")[key]
    return f"key-{key:04}"


def expected_buckets(cardinality, documents=5000, pattern="uniform"):
    counts = {category_key(key, cardinality, pattern): documents // cardinality + (key < documents % cardinality)
              for key in range(cardinality)}
    return [{"key": key, "doc_count": count} for key, count in
            sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for role in ("before", "after"):
        parser.add_argument(f"--{role}-binary", type=Path, required=True)
        parser.add_argument(f"--{role}-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--key-pattern", choices=("uniform", "benchmark"), default="uniform")
    parser.add_argument("--requests", type=int, default=100)
    args = parser.parse_args()
    if args.requests <= 0:
        parser.error("--requests must be positive")
    binaries = {role: getattr(args, role + "_binary").resolve(strict=True) for role in ORDER}
    hashes = {role: getattr(args, role + "_sha256") for role in binaries}
    for role, binary in binaries.items():
        if file_hash(binary) != hashes[role]:
            parser.error(f"{role} executable SHA-256 mismatch")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location("terms_diagnostic_matrix", ROOT / "tools/run-search-benchmark-matrix.py")
    matrix = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = matrix
    spec.loader.exec_module(matrix)
    cpu_spec = importlib.util.spec_from_file_location("terms_diagnostic_cpu", ROOT / "tools/run-core-cpu-diagnostic.py")
    cpu = importlib.util.module_from_spec(cpu_spec)
    cpu_spec.loader.exec_module(cpu)
    for key in list(os.environ):
        if key.startswith(("STEELSEARCH_", "SECURITY_")):
            del os.environ[key]
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(base, path, method="GET", body=None, ndjson=False):
        payload = body if ndjson else json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(base + path, data=payload, method=method,
                                     headers={"Content-Type": "application/x-ndjson" if ndjson else "application/json"})
        with opener.open(req, timeout=10) as response:
            return json.load(response)

    result = {"diagnostic_only": True, "acceptance_established": False,
              "key_pattern": args.key_pattern, "runner_sha256": file_hash(Path(__file__)),
              "matrix_sha256": file_hash(ROOT / "tools/run-search-benchmark-matrix.py"),
              "cpu_sampler_sha256": file_hash(ROOT / "tools/run-core-cpu-diagnostic.py"),
              "order": ORDER, "cardinalities": CARDINALITIES, "documents": 5000,
              "warmup_requests": 10, "measured_requests": args.requests,
              "binaries": {role: {"path": str(path), "sha256": hashes[role]} for role, path in binaries.items()},
              "scope": "single-client HTTP terms-only query over scalar keyword documents; not the full workload or production security profile",
              "runs": []}
    (output / "plan.json").write_text(json.dumps(result, indent=2) + "\n")
    try:
        for index, role in enumerate(ORDER):
            if file_hash(binaries[role]) != hashes[role]:
                raise ValueError("selected binary changed")
            handle = matrix.start_cluster(matrix.SCENARIOS[0], output / f"{index:02}-{role}", binaries[role])
            try:
                matrix.wait_for_cluster(matrix.SCENARIOS[0], handle.base_url, 10)
                pids = matrix.steelsearch_resource_pids(handle.process.pid, binaries[role])
                if len(pids) != 1 or file_hash(Path(f"/proc/{pids[0]}/exe")) != hashes[role]:
                    raise ValueError("actual server executable mismatch")
                run = {"role": role, "index": index, "pid": pids[0], "cases": []}
                result["runs"].append(run)
                for cardinality in CARDINALITIES:
                    name = f"terms-diagnostic-{cardinality}"
                    request(handle.base_url, "/" + name, "PUT", {
                        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                        "mappings": {"properties": {"service": {"type": "keyword"}}}})
                    for start in range(0, 5000, 500):
                        lines = []
                        for doc in range(start, start + 500):
                            lines.extend([json.dumps({"index": {"_id": str(doc)}}),
                                          json.dumps({"service": category_key(doc % cardinality, cardinality, args.key_pattern)})])
                        response = request(handle.base_url, f"/{name}/_bulk", "POST", ("\n".join(lines) + "\n").encode(), True)
                        if response.get("errors") is not False:
                            raise ValueError("bulk seed failed")
                    request(handle.base_url, f"/{name}/_refresh", "POST")
                    query = {"size": 0, "aggs": {"categories": {"terms": {"field": "service", "size": cardinality}}}}
                    expected = expected_buckets(cardinality, pattern=args.key_pattern)
                    timings = []
                    for iteration in range(10 + args.requests):
                        if iteration == 10:
                            cpu_before = cpu.cpu_sample(pids[0])
                        started = time.perf_counter_ns()
                        response = request(handle.base_url, f"/{name}/_search", "POST", query)
                        elapsed = (time.perf_counter_ns() - started) / 1e6
                        if response["aggregations"]["categories"]["buckets"] != expected:
                            raise ValueError("terms buckets differ from expected counts/order")
                        if iteration >= 10:
                            timings.append(elapsed)
                    cpu_after = cpu.cpu_sample(pids[0])
                    if cpu_before["start_ticks"] != cpu_after["start_ticks"]:
                        raise ValueError("server process identity changed")
                    cpu_seconds = sum(cpu_after[key] - cpu_before[key] for key in ("user_ticks", "system_ticks")) / os.sysconf("SC_CLK_TCK")
                    case = {"cardinality": cardinality, "milliseconds": timings,
                            "cpu_before": cpu_before, "cpu_after": cpu_after,
                            "clock_ticks_per_second": os.sysconf("SC_CLK_TCK"),
                            "server_cpu_seconds": cpu_seconds,
                            "mean_ms": statistics.mean(timings), "median_ms": statistics.median(timings)}
                    run["cases"].append(case)
                    print(index, role, cardinality, case["mean_ms"], flush=True)
                    request(handle.base_url, "/" + name, "DELETE")
                if file_hash(binaries[role]) != hashes[role]:
                    raise ValueError("selected binary changed during execution")
            finally:
                handle.stop()
        result["completed"] = True
    finally:
        (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
