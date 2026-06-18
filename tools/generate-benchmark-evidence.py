#!/usr/bin/env python3
"""Generate deterministic benchmark JSONL evidence for final release readiness."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BENCH_COMMAND = (
    "cargo",
    "bench",
    "-p",
    "os-engine-tantivy",
    "--bench",
    "deterministic_baselines",
)
EXPECTED_BENCHMARKS = (
    "index",
    "bulk",
    "refresh",
    "lexical_search",
    "aggregation",
    "exact_vector_search",
    "hnsw_vector_search",
    "hybrid_search",
    "nested_child_index_search",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "target/release-benchmarks/deterministic-benchmark-baselines.jsonl",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "target/release-benchmarks/benchmark-report.json",
    )
    parser.add_argument("--source-jsonl", type=Path, help="validate/copy an existing JSONL instead of running cargo bench")
    args = parser.parse_args()

    report, records = generate_report(
        args.root.resolve(),
        source_jsonl=args.source_jsonl,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_jsonl(records), encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["summary"]["passed"] else 1


def generate_report(
    root: Path,
    *,
    source_jsonl: Path | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    started_at = int(time.time())
    if source_jsonl is None:
        run = run_benchmark(root)
        raw_lines = run["stdout"].splitlines()
    else:
        run = {
            "command": None,
            "source_jsonl": str(source_jsonl),
            "returncode": 0,
            "stderr_tail": "",
        }
        raw_lines = source_jsonl.read_text(encoding="utf-8").splitlines()
    records, parse_errors = parse_benchmark_records(raw_lines)
    blockers = validate_records(records)
    if run["returncode"] != 0:
        blockers.append(f"benchmark command failed: returncode={run['returncode']}")
    blockers.extend(parse_errors)
    report = {
        "ready": not blockers,
        "passed": not blockers,
        "blockers": blockers,
        "summary": {
            "passed": not blockers,
            "error_count": len(blockers),
            "record_count": len(records),
            "benchmark_count": len({record.get("benchmark") for record in records}),
            "benchmarks": sorted(str(record.get("benchmark")) for record in records),
            "command_returncode": run["returncode"],
        },
        "metadata": {
            "generated_at_epoch_seconds": started_at,
            "root": str(root),
        },
        "run": run,
    }
    return report, records


def run_benchmark(root: Path) -> dict[str, Any]:
    completed = subprocess.run(
        list(BENCH_COMMAND),
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "command": list(BENCH_COMMAND),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr_tail": completed.stderr[-4000:],
    }


def parse_benchmark_records(lines: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or not stripped.startswith("{"):
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as error:
            errors.append(f"failed to parse benchmark JSONL line: {error}")
            continue
        if isinstance(payload, dict) and payload.get("benchmark"):
            records.append(payload)
    return records, errors


def validate_records(records: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if not records:
        return ["benchmark JSONL contains no benchmark records"]
    names = {str(record.get("benchmark")) for record in records}
    missing = sorted(set(EXPECTED_BENCHMARKS) - names)
    if missing:
        blockers.append(f"benchmark JSONL is missing expected records: {', '.join(missing)}")
    for record in records:
        name = record.get("benchmark")
        operations = record.get("operations")
        elapsed = record.get("elapsed_nanos")
        nanos = record.get("nanos_per_operation")
        if not isinstance(operations, int) or operations <= 0:
            blockers.append(f"{name}.operations must be a positive integer")
        if not isinstance(elapsed, int) or elapsed <= 0:
            blockers.append(f"{name}.elapsed_nanos must be a positive integer")
        if not isinstance(nanos, int) or nanos <= 0:
            blockers.append(f"{name}.nanos_per_operation must be a positive integer")
    return blockers


def render_jsonl(records: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(record, sort_keys=True) + "\n" for record in records)


if __name__ == "__main__":
    sys.exit(main())
