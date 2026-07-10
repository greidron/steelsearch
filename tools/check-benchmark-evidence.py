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
GENERATOR = ROOT / "tools/generate-benchmark-evidence.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--max-age-seconds", type=float)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = validate_benchmark_evidence(
        args.jsonl,
        args.report,
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


if __name__ == "__main__":
    sys.exit(main())
