#!/usr/bin/env python3
"""Validate current deterministic benchmark evidence without rerunning benches."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = ROOT / "target/release-benchmarks/deterministic-benchmark-baselines.jsonl"
DEFAULT_REPORT = ROOT / "target/release-benchmarks/benchmark-report.json"
DEFAULT_COMPARISON_SUMMARY = ROOT / "target/search-benchmark-matrix-current-20260630T023334Z/summary.json"
GENERATOR = ROOT / "tools/generate-benchmark-evidence.py"
REQUIRED_COMPARISON_TOPOLOGIES = ("single-node", "three-node")
REQUIRED_COMPARISON_LATENCY_METRICS = ("p50_ms", "p95_ms", "p99_ms", "mean_ms")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--comparison-summary", type=Path)
    parser.add_argument("--max-age-seconds", type=float)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = validate_benchmark_evidence(
        args.jsonl,
        args.report,
        comparison_summary_path=args.comparison_summary,
        max_age_seconds=args.max_age_seconds,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["summary"]["passed"] else 1


def validate_benchmark_evidence(
    jsonl_path: Path,
    report_path: Path,
    *,
    comparison_summary_path: Path | None = None,
    max_age_seconds: float | None = None,
) -> dict[str, Any]:
    generator = load_generator()
    records, parse_errors = load_records(generator, jsonl_path)
    errors = []
    errors.extend(file_errors(jsonl_path, "benchmark JSONL", max_age_seconds))
    errors.extend(file_errors(report_path, "benchmark report", max_age_seconds))
    errors.extend(parse_errors)
    errors.extend(generator.validate_records(records))

    report_payload = load_json(report_path)
    if not isinstance(report_payload, dict):
        errors.append("benchmark report is not parseable JSON object")
    else:
        errors.extend(report_payload_errors(report_payload, records))

    comparison_summary = load_json(comparison_summary_path) if comparison_summary_path else None
    comparison_coverage = comparison_summary_coverage(comparison_summary)
    if comparison_summary_path is not None:
        if not comparison_summary_path.is_file():
            errors.append(f"benchmark comparison summary is missing: {comparison_summary_path}")
        elif not isinstance(comparison_summary, dict):
            errors.append("benchmark comparison summary is not parseable JSON object")
        errors.extend(comparison_summary_errors(comparison_summary))

    benchmark_names = sorted(
        str(record.get("benchmark"))
        for record in records
        if isinstance(record, dict) and record.get("benchmark")
    )
    summary = {
        "passed": not errors,
        "error_count": len(errors),
        "record_count": len(records),
        "benchmark_count": len(set(benchmark_names)),
        "benchmarks": sorted(set(benchmark_names)),
        "comparison_summary": str(comparison_summary_path) if comparison_summary_path else None,
        "comparison_topologies": comparison_coverage["topologies"],
        "comparison_operation_count": comparison_coverage["operation_count"],
        "comparison_rss_peak_ratio_count": comparison_coverage["rss_peak_ratio_count"],
        "comparison_bottleneck_count": comparison_coverage["bottleneck_count"],
        "comparison_worst_throughput_ratio": comparison_coverage["worst_throughput_ratio"],
        "comparison_worst_latency_ratio": comparison_coverage["worst_latency_ratio"],
        "jsonl_age_seconds": file_age_seconds(jsonl_path),
        "report_age_seconds": file_age_seconds(report_path),
        "max_age_seconds": max_age_seconds,
    }
    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "jsonl": str(jsonl_path),
        "report": str(report_path),
        "summary": summary,
    }


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_benchmark_evidence", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["generate_benchmark_evidence"] = module
    spec.loader.exec_module(module)
    return module


def load_records(generator, path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.is_file():
        return [], [f"benchmark JSONL is missing: {path}"]
    return generator.parse_benchmark_records(path.read_text(encoding="utf-8").splitlines())


def file_errors(path: Path, label: str, max_age_seconds: float | None) -> list[str]:
    if not path.is_file():
        return [f"{label} is missing: {path}"]
    if max_age_seconds is None:
        return []
    age_seconds = file_age_seconds(path)
    if age_seconds is not None and age_seconds > max_age_seconds:
        return [
            f"{label} is stale: age_seconds={age_seconds:.0f} "
            f"max_age_seconds={max_age_seconds:.0f}"
        ]
    return []


def file_age_seconds(path: Path) -> float | None:
    if not path.is_file():
        return None
    return round(max(0.0, time.time() - path.stat().st_mtime), 3)


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def report_payload_errors(
    report: dict[str, Any],
    records: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    summary = report.get("summary")
    if not isinstance(summary, dict):
        return ["benchmark report summary is missing"]
    if summary.get("passed") is not True:
        errors.append("benchmark report summary.passed is not true")
    if summary.get("error_count") != 0:
        errors.append(f"benchmark report summary.error_count={summary.get('error_count')}")
    if summary.get("command_returncode") != 0:
        errors.append(
            f"benchmark report summary.command_returncode={summary.get('command_returncode')}"
        )
    record_names = sorted(
        str(record.get("benchmark"))
        for record in records
        if isinstance(record, dict) and record.get("benchmark")
    )
    if summary.get("record_count") != len(records):
        errors.append("benchmark report summary.record_count drift")
    if summary.get("benchmark_count") != len(set(record_names)):
        errors.append("benchmark report summary.benchmark_count drift")
    if sorted(summary.get("benchmarks") or []) != sorted(set(record_names)):
        errors.append("benchmark report summary.benchmarks drift")
    return errors


def comparison_summary_coverage(report: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(report, dict):
        return empty_comparison_coverage()
    comparisons = report.get("comparisons")
    if not isinstance(comparisons, dict):
        return empty_comparison_coverage()
    operation_count = 0
    rss_peak_ratio_count = 0
    bottleneck_count = 0
    throughput_ratios: list[float] = []
    latency_ratios: list[float] = []
    for payload in comparisons.values():
        if not isinstance(payload, dict):
            continue
        operations = payload.get("operations")
        if isinstance(operations, dict):
            operation_count += len(operations)
            for operation_payload in operations.values():
                if not isinstance(operation_payload, dict):
                    continue
                throughput_ratio = (
                    (operation_payload.get("throughput_ops_per_second") or {}).get("ratio")
                )
                if positive_number(throughput_ratio):
                    throughput_ratios.append(float(throughput_ratio))
                for metric in REQUIRED_COMPARISON_LATENCY_METRICS:
                    latency_ratio = (operation_payload.get(metric) or {}).get("ratio")
                    if positive_number(latency_ratio):
                        latency_ratios.append(float(latency_ratio))
        rss_peak_ratio = (
            ((payload.get("resource_usage") or {}).get("memory_rss_bytes") or {})
            .get("peak", {})
            .get("ratio")
        )
        if positive_number(rss_peak_ratio):
            rss_peak_ratio_count += 1
        throughput_ratio = (payload.get("throughput_ops_per_second") or {}).get("ratio")
        if positive_number(throughput_ratio):
            throughput_ratios.append(float(throughput_ratio))
        bottlenecks = payload.get("steelsearch_slower_than_opensearch")
        if isinstance(bottlenecks, list):
            bottleneck_count += len(bottlenecks)
    return {
        "topologies": sorted(str(name) for name in comparisons),
        "operation_count": operation_count,
        "rss_peak_ratio_count": rss_peak_ratio_count,
        "bottleneck_count": bottleneck_count,
        "worst_throughput_ratio": min(throughput_ratios) if throughput_ratios else None,
        "worst_latency_ratio": max(latency_ratios) if latency_ratios else None,
    }


def empty_comparison_coverage() -> dict[str, Any]:
    return {
        "topologies": [],
        "operation_count": 0,
        "rss_peak_ratio_count": 0,
        "bottleneck_count": 0,
        "worst_throughput_ratio": None,
        "worst_latency_ratio": None,
    }


def comparison_summary_errors(report: dict[str, Any] | None) -> list[str]:
    if not isinstance(report, dict):
        return []
    comparisons = report.get("comparisons")
    if not isinstance(comparisons, dict) or not comparisons:
        return ["benchmark comparison summary.comparisons is missing or empty"]
    errors: list[str] = []
    for topology in REQUIRED_COMPARISON_TOPOLOGIES:
        payload = comparisons.get(topology)
        if not isinstance(payload, dict):
            errors.append(f"benchmark comparison missing topology {topology}")
            continue
        throughput = (payload.get("throughput_ops_per_second") or {}).get("ratio")
        if not positive_number(throughput):
            errors.append(f"{topology}: throughput ratio is missing or non-positive")
        rss_peak = (
            ((payload.get("resource_usage") or {}).get("memory_rss_bytes") or {})
            .get("peak", {})
            .get("ratio")
        )
        if not positive_number(rss_peak):
            errors.append(f"{topology}: RSS peak ratio is missing or non-positive")
        operations = payload.get("operations")
        if not isinstance(operations, dict) or not operations:
            errors.append(f"{topology}: operation comparison ratios are missing")
            continue
        expected_bottlenecks = expected_steelsearch_bottlenecks(payload)
        observed_bottlenecks = payload.get("steelsearch_slower_than_opensearch")
        if not isinstance(observed_bottlenecks, list):
            errors.append(f"{topology}: steelsearch slower-than-opensearch bottleneck list is missing")
        else:
            observed_keys = sorted(bottleneck_key(item) for item in observed_bottlenecks)
            expected_keys = sorted(bottleneck_key(item) for item in expected_bottlenecks)
            if observed_keys != expected_keys:
                errors.append(
                    f"{topology}: steelsearch slower-than-opensearch bottleneck list drift"
                )
        for operation, operation_payload in sorted(operations.items()):
            if not isinstance(operation_payload, dict):
                errors.append(f"{topology}:{operation}: operation payload is not an object")
                continue
            throughput_ratio = (
                (operation_payload.get("throughput_ops_per_second") or {}).get("ratio")
            )
            if not positive_number(throughput_ratio):
                errors.append(f"{topology}:{operation}: throughput ratio is missing or non-positive")
            for metric in REQUIRED_COMPARISON_LATENCY_METRICS:
                ratio_value = (operation_payload.get(metric) or {}).get("ratio")
                if not positive_number(ratio_value):
                    errors.append(f"{topology}:{operation}: {metric} ratio is missing or non-positive")
    return errors


def expected_steelsearch_bottlenecks(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    slower: list[dict[str, Any]] = []
    throughput = comparison.get("throughput_ops_per_second") or {}
    ratio = throughput.get("ratio")
    if positive_number(ratio) and ratio < 1.0:
        slower.append(
            {
                "operation": "overall",
                "metric": "throughput_ops_per_second",
                "direction": "lower_is_worse",
            }
        )
    operations = comparison.get("operations")
    if not isinstance(operations, dict):
        return slower
    for operation, operation_payload in sorted(operations.items()):
        if not isinstance(operation_payload, dict):
            continue
        throughput = operation_payload.get("throughput_ops_per_second") or {}
        ratio = throughput.get("ratio")
        if positive_number(ratio) and ratio < 1.0:
            slower.append(
                {
                    "operation": str(operation),
                    "metric": "throughput_ops_per_second",
                    "direction": "lower_is_worse",
                }
            )
        for metric in REQUIRED_COMPARISON_LATENCY_METRICS:
            values = operation_payload.get(metric) or {}
            ratio = values.get("ratio")
            if positive_number(ratio) and ratio > 1.0:
                slower.append(
                    {
                        "operation": str(operation),
                        "metric": metric,
                        "direction": "higher_is_worse",
                    }
                )
    return slower


def bottleneck_key(item: Any) -> tuple[str, str, str]:
    if not isinstance(item, dict):
        return ("<invalid>", "<invalid>", "<invalid>")
    return (
        str(item.get("operation")),
        str(item.get("metric")),
        str(item.get("direction")),
    )


def positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


if __name__ == "__main__":
    sys.exit(main())
