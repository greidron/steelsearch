#!/usr/bin/env python3
"""Generate and validate evidence-backed release performance tables."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

START = "<!-- release-performance:start -->"
END = "<!-- release-performance:end -->"
OPERATIONS = ("write", "lexical", "ranking", "facet", "sort_filter", "nested", "refresh")
TOPOLOGIES = ("single-node", "three-node")
REPORTS = ("current", "previous", "opensearch")
TAG = re.compile(r"v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path}: expected an object")
    return value


def positive(value, label: str) -> float:
    require(type(value) in (int, float) and math.isfinite(value) and value > 0,
            f"{label}: expected a finite positive number")
    return float(value)


def count(value, label: str) -> int:
    require(type(value) is int and value > 0, f"{label}: expected a positive integer")
    return value


def text(value, label: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{label}: required")
    require(not any(marker in value.upper() for marker in ("TODO", "TBD", "PLACEHOLDER")),
            f"{label}: replace placeholders")
    require(not any(c in value for c in ("\n", "\r", "|", "<", ">")),
            f"{label}: use plain single-line text")
    return value


def query_weights(value) -> dict:
    if isinstance(value, str):
        pairs = [item.split("=") for item in value.split(",")]
        require(all(len(pair) == 2 for pair in pairs), "invalid query mix")
        require(len({pair[0] for pair in pairs}) == len(pairs), "duplicate query weights")
        value = {key: int(weight) for key, weight in pairs}
    require(isinstance(value, dict), "query mix must be an object or weight list")
    require(all(type(weight) is int and weight >= 0 for weight in value.values()),
            "query weights must be nonnegative integers")
    return {key: weight for key, weight in value.items() if weight}


def performance_section(directory: Path) -> str:
    manifest = load(directory / "release.json")
    require(manifest.get("schema_version") == 1, "unsupported release schema")
    for key in ("release", "previous_release"):
        require(isinstance(manifest.get(key), str) and TAG.fullmatch(manifest[key]), f"invalid {key}")
    require(manifest["release"] != manifest["previous_release"], "previous release must differ")
    require(manifest.get("support_profile") == "core-no-plugins", "only core-no-plugins is supported")
    for key in ("opensearch_version", "environment", "runtime_settings", "comparison_limits"):
        text(manifest.get(key), key)
    reports = {name: load(directory / f"{name}.json") for name in REPORTS}
    configs = []
    rows = []
    hashes = {}
    for name, report in reports.items():
        require(not report.get("diagnostic_only", False), f"{name}: diagnostic profiling is not release evidence")
        config = report["config"]
        weights = query_weights(config["query_mix"])
        require(set(weights) == set(OPERATIONS), f"{name}: all seven core operations, no plugins, required")
        normalized = {key: config[key] for key in (
            "corpus_size", "vector_dimension", "duration_seconds", "clients", "number_of_shards", "number_of_replicas", "seed"
        )}
        for key in ("corpus_size", "vector_dimension", "duration_seconds", "clients", "number_of_shards"):
            positive(normalized[key], f"{name}.{key}")
        require(type(normalized["number_of_replicas"]) is int and normalized["number_of_replicas"] >= 0,
                f"{name}: replicas must be a nonnegative integer")
        normalized["query_mix"] = weights
        configs.append(normalized)
        engine = "opensearch" if name == "opensearch" else "steelsearch"
        for topology in TOPOLOGIES:
            scenario = report["scenarios"][f"{engine}-{topology}"]
            require(not scenario.get("diagnostic_only", False),
                    f"{name}/{topology}: diagnostic profiling is not release evidence")
            executed = scenario["config"]
            for key in ("corpus_size", "vector_dimension", "duration_seconds", "clients", "number_of_shards", "seed"):
                require(executed[key] == config[key], f"{name}/{topology}: executed {key} differs")
            replicas = 0 if topology == "single-node" else min(config["number_of_replicas"], 2)
            require(executed["number_of_replicas"] == replicas, f"{name}/{topology}: executed replicas differ")
            require(query_weights(executed["query_mix"]) == weights,
                    f"{name}/{topology}: executed workload differs")
            if engine == "steelsearch":
                executable = scenario["executable"]
                digest = executable["sha256"]
                require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest),
                        f"{name}/{topology}: executable SHA-256 required")
                text(executable["path"], "executable path")
                require(name not in hashes or hashes[name] == digest, f"{name}: mixed executables")
                hashes[name] = digest
            else:
                require(scenario["target_identity"]["version"]["number"] == manifest["opensearch_version"],
                        "OpenSearch identity does not match declared version")
            summary = scenario["summary"]
            require(summary["error_count"] == 0 and summary["error_rate"] == 0,
                    f"{name}/{topology}: benchmark request errors")
            successful = count(summary["success_count"], "successful requests")
            elapsed = positive(summary["elapsed_seconds"], "elapsed seconds")
            throughput = positive(summary["throughput_ops_per_second"], "throughput")
            require(math.isclose(throughput, summary["success_count"] / elapsed, rel_tol=1e-6),
                    "throughput does not match request count and elapsed time")
            require(count(summary["operation_count"], "total requests") == successful,
                    f"{name}/{topology}: total request count differs from successes")
            require(set(scenario["operations"]) == set(OPERATIONS),
                    f"{name}/{topology}: exactly seven core operation results required")
            operation_samples = 0
            for operation in OPERATIONS:
                result = scenario["operations"][operation]
                require(result["error_count"] == 0, f"{name}/{topology}/{operation}: errors")
                samples = count(result["success_count"], "operation samples")
                require(count(result["latency_ms"]["count"], "latency samples") == samples,
                        f"{name}/{topology}/{operation}: latency sample count differs")
                operation_samples += samples
                positive(result["latency_ms"]["mean"], "mean latency")
                positive(result["latency_ms"]["p95"], "p95 latency")
            require(operation_samples == successful,
                    f"{name}/{topology}: operation counts do not sum to successful requests")
    require(all(config == configs[0] for config in configs), "benchmark workload configurations differ")
    require(hashes["current"] != hashes["previous"],
            "current and previous use the same executable; verify release binary selection")
    config = configs[0]

    def scenario(name, topology):
        engine = "opensearch" if name == "opensearch" else "steelsearch"
        return reports[name]["scenarios"][f"{engine}-{topology}"]

    rows.extend([
        START, "## Performance", "",
        f"- Current: `{manifest['release']}`; previous published release: `{manifest['previous_release']}`.",
        f"- Reference: OpenSearch `{manifest['opensearch_version']}`; support: `core-no-plugins`.",
        f"- Environment: {manifest['environment']}",
        f"- Runtime and durability settings: {manifest['runtime_settings']}",
        f"- Limits: {manifest['comparison_limits']}",
        f"- Workload: {config['corpus_size']} documents, {config['clients']} clients, "
        f"{config['duration_seconds']} seconds per topology, {config['number_of_shards']} shards; "
        f"replicas: 0 on one node, {min(config['number_of_replicas'], 2)} on three nodes; seed {config['seed']}.",
        "- Operation weights: " + ", ".join(f"{key}={config['query_mix'][key]}" for key in OPERATIONS) + ".",
        f"- Synthetic source embedding array: {config['vector_dimension']} numbers per document; no k-NN index or requests.",
        f"- Current binary SHA-256: `{hashes['current']}`.",
        f"- Previous binary SHA-256: `{hashes['previous']}`.",
        "- Raw reports and release metadata: attached `performance-evidence.zip`.", "",
        "### Throughput", "",
        "Higher is better. Change = (current / previous - 1) * 100; ratio = current / OpenSearch.", "",
        "| Topology | Previous ops/s | Current ops/s | Change | OpenSearch ops/s | Ratio |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ])
    for topology in TOPOLOGIES:
        current, previous, reference = [scenario(name, topology)["summary"]["throughput_ops_per_second"]
                                        for name in REPORTS]
        rows.append(f"| {topology} | {previous:.2f} | {current:.2f} | "
                    f"{100 * (current / previous - 1):+.2f}% | {reference:.2f} | {current / reference:.2f}x |")
    rows.extend([
        "", "### Scenario Latency", "",
        "Mean milliseconds, lower is better. Positive change is a regression; "
        "speedup = OpenSearch / current. Throughput is not per-operation latency.", "",
        "| Topology | Scenario | Previous ms | Current ms | Change | OpenSearch ms | Speedup | Current p95 ms |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for topology in TOPOLOGIES:
        for operation in OPERATIONS:
            metrics = [scenario(name, topology)["operations"][operation]["latency_ms"] for name in REPORTS]
            current, previous, reference = [metric["mean"] for metric in metrics]
            rows.append(f"| {topology} | {operation} | {previous:.2f} | {current:.2f} | "
                        f"{100 * (current / previous - 1):+.2f}% | {reference:.2f} | "
                        f"{reference / current:.2f}x | {metrics[0]['p95']:.2f} |")
    rows.extend(["", END])
    return "\n".join(rows)


def validate_notes(directory: Path, render: bool = False) -> None:
    generated = performance_section(directory)
    path = directory / "notes.md"
    notes = path.read_text(encoding="utf-8")
    require(notes.count(START) == 1 and notes.count(END) == 1, "exactly one performance marker pair required")
    begin, end = notes.index(START), notes.index(END) + len(END)
    require(begin < end - len(END), "performance markers out of order")
    manifest = load(directory / "release.json")
    require(notes.startswith(f"# SteelSearch {manifest['release']}\n"), "release title mismatch")
    for heading in ("## Changes", "## Compatibility", "## Validation", "## Known Limitations"):
        require(heading in notes, f"missing section: {heading}")
        content = notes.split(heading, 1)[1].split("\n## ", 1)[0].strip()
        content = content.split(START, 1)[0].strip()
        require(bool(content) and not any(x in content.upper() for x in ("TODO", "TBD", "PLACEHOLDER")),
                f"empty or placeholder section: {heading}")
    if render:
        path.write_text(notes[:begin] + generated + notes[end:], encoding="utf-8")
    else:
        require(notes[begin:end] == generated, "performance table missing, stale or edited; run --render")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    try:
        validate_notes(args.directory, args.render)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f"release notes rejected: {error}\n")
    print("Release notes and performance evidence validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
