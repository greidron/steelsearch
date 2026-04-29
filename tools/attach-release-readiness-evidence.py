#!/usr/bin/env python3
"""Attach benchmark/load evidence to a Steelsearch readiness report."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readiness-report", required=True)
    parser.add_argument("--benchmark-report")
    parser.add_argument("--load-report")
    parser.add_argument("--load-comparison-report")
    parser.add_argument("--max-age-seconds", type=float, default=86_400.0)
    args = parser.parse_args()

    report_path = Path(args.readiness_report)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    evidence = {
        "benchmark": inspect_jsonl_report(args.benchmark_report, args.max_age_seconds),
        "load": inspect_json_report(args.load_report, args.max_age_seconds),
        "load_comparison": inspect_json_report(args.load_comparison_report, args.max_age_seconds),
    }
    blockers = [
        f"{name}: {blocker}"
        for name, item in evidence.items()
        for blocker in item.get("blockers", [])
    ]

    report["release_evidence"] = evidence
    categories = report.setdefault("categories", {})
    release = categories.setdefault("release", {"ready": False, "blockers": []})
    release["evidence"] = evidence
    existing_release_blockers = release.get("blockers", [])
    release["blockers"] = sorted(set(existing_release_blockers + blockers))
    release["ready"] = len(release["blockers"]) == 0

    report["ready"] = all(
        category.get("ready") is True
        for category in categories.values()
        if isinstance(category, dict)
    )
    report["blockers"] = readiness_blockers(categories)

    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def inspect_jsonl_report(path_value: str | None, max_age_seconds: float) -> dict[str, Any]:
    base = inspect_file(path_value, max_age_seconds)
    if base["blockers"]:
        return base

    records = []
    try:
        for line in Path(path_value or "").read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    except Exception as error:  # noqa: BLE001 - evidence parser reports blocker
        base["blockers"].append(f"failed to parse JSONL report: {error}")
        return base

    if not records:
        base["blockers"].append("report contains no benchmark records")
    base["record_count"] = len(records)
    base["benchmarks"] = sorted(
        str(record.get("benchmark"))
        for record in records
        if isinstance(record, dict) and record.get("benchmark")
    )
    base["ready"] = len(base["blockers"]) == 0
    return base


def inspect_json_report(path_value: str | None, max_age_seconds: float) -> dict[str, Any]:
    base = inspect_file(path_value, max_age_seconds)
    if base["blockers"]:
        return base

    try:
        payload = json.loads(Path(path_value or "").read_text(encoding="utf-8"))
    except Exception as error:  # noqa: BLE001 - evidence parser reports blocker
        base["blockers"].append(f"failed to parse JSON report: {error}")
        return base

    base["summary"] = summarize_json_payload(payload)
    for blocker in json_payload_blockers(payload):
        base["blockers"].append(blocker)
    base["ready"] = len(base["blockers"]) == 0
    return base


def inspect_file(path_value: str | None, max_age_seconds: float) -> dict[str, Any]:
    if not path_value:
        return {"ready": False, "path": None, "blockers": ["report path is not configured"]}
    path = Path(path_value)
    result: dict[str, Any] = {"ready": False, "path": str(path), "blockers": []}
    if not path.exists():
        result["blockers"].append("report file is missing")
        return result
    modified_at = path.stat().st_mtime
    age_seconds = time.time() - modified_at
    result["modified_at_epoch_seconds"] = modified_at
    result["age_seconds"] = age_seconds
    if age_seconds > max_age_seconds:
        result["blockers"].append(
            f"report is stale: age_seconds={age_seconds:.0f} max_age_seconds={max_age_seconds:.0f}"
        )
    result["ready"] = len(result["blockers"]) == 0
    return result


def summarize_json_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"type": type(payload).__name__}
    summary = payload.get("summary")
    if isinstance(summary, dict):
        return summary
    comparison = payload.get("comparison")
    if isinstance(comparison, dict):
        return {"comparison_mode": comparison.get("mode")}
    return {"top_level_keys": sorted(payload.keys())}


def json_payload_blockers(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["report payload is not a JSON object"]
    blockers: list[str] = []
    summary = payload.get("summary")
    if isinstance(summary, dict) and summary.get("error_count", 0):
        blockers.append(f"load report has errors: {summary.get('error_count')}")
    targets = payload.get("targets")
    if isinstance(targets, dict):
        for name, target in targets.items():
            if isinstance(target, dict) and target.get("returncode", 0) != 0:
                blockers.append(f"{name} load comparison returncode={target.get('returncode')}")
    return blockers


def readiness_blockers(categories: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for name, category in categories.items():
        if not isinstance(category, dict):
            continue
        for blocker in category.get("blockers", []):
            blockers.append(f"{name}: {blocker}")
    return sorted(set(blockers))


if __name__ == "__main__":
    raise SystemExit(main())
