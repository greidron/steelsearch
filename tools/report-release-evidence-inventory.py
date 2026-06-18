#!/usr/bin/env python3
"""Inventory release-readiness evidence artifacts before final cutover."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


STARTUP_ITEMS = {
    "benchmark_coverage": {
        "artifact_kind": "benchmark JSONL",
        "patterns": ("**/*benchmark*.jsonl",),
        "attach_argument": "--benchmark-report",
    },
    "load_test_coverage": {
        "artifact_kind": "load JSON",
        "patterns": ("**/*load*.json",),
        "exclude_name_parts": ("comparison",),
        "attach_argument": "--load-report",
    },
    "chaos_test_coverage": {
        "artifact_kind": "chaos JSON",
        "patterns": ("**/*chaos*.json",),
        "attach_argument": "--chaos-report",
    },
    "packaging_verified": {
        "artifact_kind": "packaging JSON",
        "patterns": ("**/*packaging*.json",),
        "attach_argument": "--packaging-report",
    },
    "rolling_upgrade_coverage": {
        "artifact_kind": "rolling-upgrade JSON",
        "patterns": ("**/*rolling*upgrade*.json", "**/*rolling*.json"),
        "attach_argument": "--rolling-upgrade-report",
    },
}
READINESS_ONLY_ITEMS = {
    "load_comparison": {
        "artifact_kind": "Steelsearch-vs-OpenSearch load comparison JSON",
        "patterns": ("**/*load-comparison*.json", "**/*load*comparison*.json"),
        "attach_argument": "--load-comparison-report",
    },
}
ALL_ITEMS = {**STARTUP_ITEMS, **READINESS_ONLY_ITEMS}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("target"))
    parser.add_argument("--max-age-seconds", type=float, default=86_400.0)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = build_inventory(
        args.root,
        max_age_seconds=args.max_age_seconds,
        require_complete=args.require_complete,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["summary"]["passed"] else 1


def build_inventory(
    root: Path,
    *,
    max_age_seconds: float,
    require_complete: bool = False,
    now: float | None = None,
) -> dict[str, Any]:
    now = time.time() if now is None else now
    root = root.resolve()
    items = {
        name: inspect_item(root, name, spec, max_age_seconds=max_age_seconds, now=now)
        for name, spec in ALL_ITEMS.items()
    }
    missing_startup = [
        name for name in STARTUP_ITEMS if not items[name]["ready"]
    ]
    missing_readiness = [
        name for name in ALL_ITEMS if not items[name]["ready"]
    ]
    complete = not missing_readiness
    passed = complete if require_complete else True
    return {
        "summary": {
            "passed": passed,
            "complete": complete,
            "require_complete": require_complete,
            "root": str(root),
            "max_age_seconds": max_age_seconds,
            "startup_missing_items": missing_startup,
            "readiness_attachment_missing_items": missing_readiness,
        },
        "items": items,
        "attach_command_template": attach_command_template(items),
    }


def inspect_item(
    root: Path,
    name: str,
    spec: dict[str, Any],
    *,
    max_age_seconds: float,
    now: float,
) -> dict[str, Any]:
    candidates = sorted(
        unique_paths(
            candidate
            for pattern in spec["patterns"]
            for candidate in root.glob(pattern)
            if candidate.is_file() and not excluded_candidate(candidate, spec)
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    latest = candidates[0] if candidates else None
    blockers: list[str] = []
    if latest is None:
        blockers.append("artifact candidate is missing")
        age_seconds = None
    else:
        age_seconds = now - latest.stat().st_mtime
        if age_seconds > max_age_seconds:
            blockers.append(
                f"latest artifact is stale: age_seconds={age_seconds:.0f} max_age_seconds={max_age_seconds:.0f}"
            )
        blockers.extend(validate_artifact_shape(name, latest))
    return {
        "name": name,
        "artifact_kind": spec["artifact_kind"],
        "attach_argument": spec["attach_argument"],
        "ready": not blockers,
        "blockers": blockers,
        "candidate_count": len(candidates),
        "latest_artifact_path": str(latest) if latest else None,
        "latest_artifact_age_seconds": age_seconds,
    }


def excluded_candidate(path: Path, spec: dict[str, Any]) -> bool:
    name = path.name.lower()
    return any(part in name for part in spec.get("exclude_name_parts", ()))


def validate_artifact_shape(name: str, path: Path) -> list[str]:
    if name == "benchmark_coverage":
        return validate_benchmark_jsonl(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:  # noqa: BLE001 - inventory reports blocker
        return [f"artifact is not parseable JSON: {error}"]
    if not isinstance(payload, dict):
        return ["artifact payload is not a JSON object"]
    if name == "load_test_coverage":
        return validate_load_json(payload)
    if name == "load_comparison":
        return validate_load_comparison_json(payload)
    if name == "chaos_test_coverage":
        return validate_chaos_json(payload)
    if name == "rolling_upgrade_coverage":
        return validate_rolling_upgrade_json(payload)
    return validate_generic_json_evidence(payload)


def validate_benchmark_jsonl(path: Path) -> list[str]:
    records: list[Any] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    except Exception as error:  # noqa: BLE001 - inventory reports blocker
        return [f"artifact is not parseable JSONL: {error}"]
    if not records:
        return ["benchmark JSONL contains no records"]
    if not any(isinstance(record, dict) and record.get("benchmark") for record in records):
        return ["benchmark JSONL contains no named benchmark records"]
    return []


def validate_load_json(payload: dict[str, Any]) -> list[str]:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return ["load JSON summary is missing"]
    errors: list[str] = []
    if summary.get("error_count", 0) != 0:
        errors.append(f"load JSON summary.error_count={summary.get('error_count')}")
    if not isinstance(summary.get("operation_count"), (int, float)):
        errors.append("load JSON summary.operation_count is missing")
    return errors


def validate_load_comparison_json(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    targets = payload.get("targets")
    comparison = payload.get("comparison")
    if not isinstance(targets, dict):
        errors.append("load comparison targets are missing")
    else:
        for name in ("steelsearch", "opensearch"):
            target = targets.get(name)
            if not isinstance(target, dict):
                errors.append(f"load comparison target is missing: {name}")
            elif target.get("returncode", 0) != 0:
                errors.append(f"load comparison {name}.returncode={target.get('returncode')}")
    if not isinstance(comparison, dict):
        errors.append("load comparison comparison object is missing")
    elif comparison.get("mode") == "dry-run":
        errors.append("load comparison is a dry-run report")
    return errors


def validate_chaos_json(payload: dict[str, Any]) -> list[str]:
    errors = validate_generic_json_evidence(payload)
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        errors.append("chaos summary is missing")
    elif summary.get("coverage_scope") != "mixed-cluster failure fixture":
        errors.append("chaos coverage_scope mismatch")
    source = payload.get("source_report")
    if not isinstance(source, dict):
        errors.append("chaos source_report is missing")
    elif source.get("summary", {}).get("passed") is not True:
        errors.append("chaos source_report summary.passed is not true")
    return errors


def validate_rolling_upgrade_json(payload: dict[str, Any]) -> list[str]:
    errors = validate_generic_json_evidence(payload)
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        errors.append("rolling-upgrade summary is missing")
    elif summary.get("coverage_scope") != "rolling-upgrade transcript fixture":
        errors.append("rolling-upgrade coverage_scope mismatch")
    transcript = payload.get("transcript")
    if not isinstance(transcript, dict):
        errors.append("rolling-upgrade transcript is missing")
    elif transcript.get("profile") != "rolling-upgrade":
        errors.append("rolling-upgrade transcript profile mismatch")
    return errors


def validate_generic_json_evidence(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = payload.get("summary")
    if isinstance(summary, dict) and summary.get("error_count", 0) != 0:
        errors.append(f"evidence summary.error_count={summary.get('error_count')}")
    blockers = payload.get("blockers")
    if isinstance(blockers, list) and blockers:
        errors.append("evidence blockers is not empty")
    if payload.get("ready") is False or payload.get("passed") is False:
        errors.append("evidence reports ready/passed false")
    return errors


def unique_paths(paths: Any) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        result.append(path)
    return result


def attach_command_template(items: dict[str, dict[str, Any]]) -> list[str]:
    command = [
        "python3",
        "tools/attach-release-readiness-evidence.py",
        "--readiness-report",
        "<readiness-report.json>",
    ]
    ordered = [
        "benchmark_coverage",
        "load_test_coverage",
        "load_comparison",
        "chaos_test_coverage",
        "packaging_verified",
        "rolling_upgrade_coverage",
    ]
    for name in ordered:
        item = items[name]
        command.extend(
            [
                item["attach_argument"],
                item["latest_artifact_path"] or f"<{name}>",
            ]
        )
    command.extend(["--release-readiness-file", "<release-readiness.json>"])
    return command


if __name__ == "__main__":
    raise SystemExit(main())
