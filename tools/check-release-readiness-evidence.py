#!/usr/bin/env python3
"""Validate the release-readiness evidence manifest used by production startup."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_ITEMS = (
    "benchmark_coverage",
    "load_test_coverage",
    "chaos_test_coverage",
    "packaging_verified",
    "rolling_upgrade_coverage",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--require-passed", action="store_true")
    args = parser.parse_args()

    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = validate_manifest(
        payload,
        manifest_path=args.manifest,
        require_passed=args.require_passed,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "ok" else 1


def validate_manifest(
    payload: dict[str, Any],
    *,
    manifest_path: Path,
    require_passed: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    evidence_root = manifest_path.parent
    items: dict[str, dict[str, Any]] = {}

    if not isinstance(payload, dict):
        errors.append("manifest payload is not a JSON object")
        return build_report(errors, items)

    missing = sorted(set(REQUIRED_ITEMS) - set(payload))
    extra = sorted(set(payload) - set(REQUIRED_ITEMS))
    for name in missing:
        errors.append(f"{name} is missing")
    for name in extra:
        errors.append(f"{name} is not a recognized release-readiness item")

    for name in REQUIRED_ITEMS:
        raw = payload.get(name)
        if not isinstance(raw, dict):
            if name not in missing:
                errors.append(f"{name} must be an object")
            continue
        item_report = validate_item(
            name,
            raw,
            evidence_root=evidence_root,
            require_passed=require_passed,
        )
        items[name] = item_report
        errors.extend(item_report["errors"])

    return build_report(errors, items)


def validate_item(
    name: str,
    item: dict[str, Any],
    *,
    evidence_root: Path,
    require_passed: bool,
) -> dict[str, Any]:
    errors: list[str] = []
    passed = item.get("passed")
    artifact_path = item.get("artifact_path")
    blockers = item.get("blockers", [])
    summary = item.get("summary")

    if not isinstance(passed, bool):
        errors.append(f"{name}.passed must be a boolean")
    elif require_passed and not passed:
        errors.append(f"{name}.passed is false")

    if not isinstance(artifact_path, str) or not artifact_path:
        errors.append(f"{name}.artifact_path must be a non-empty string")
        resolved_artifact = None
    else:
        path = Path(artifact_path)
        resolved_artifact = path if path.is_absolute() else evidence_root / path
        if not resolved_artifact.is_file():
            errors.append(f"{name}.artifact_path is not a readable file: {resolved_artifact}")

    if not isinstance(blockers, list):
        errors.append(f"{name}.blockers must be a list")
    elif require_passed and blockers:
        errors.append(f"{name}.blockers is not empty")

    if name == "benchmark_coverage":
        record_count = item.get("record_count")
        benchmarks = item.get("benchmarks")
        if not isinstance(record_count, int) or record_count < 1:
            errors.append(f"{name}.record_count must be a positive integer")
        if not isinstance(benchmarks, list) or not benchmarks:
            errors.append(f"{name}.benchmarks must be a non-empty list")
    elif not isinstance(summary, dict) or not summary:
        errors.append(f"{name}.summary must be a non-empty object")

    return {
        "passed": passed,
        "artifact_path": artifact_path,
        "resolved_artifact_path": str(resolved_artifact) if resolved_artifact else None,
        "blocker_count": len(blockers) if isinstance(blockers, list) else None,
        "summary_present": isinstance(summary, dict) and bool(summary),
        "errors": errors,
    }


def build_report(errors: list[str], items: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary": {
            "required_items": len(REQUIRED_ITEMS),
            "checked_items": len(items),
            "ready_items": sum(1 for item in items.values() if item.get("passed") is True),
        },
        "items": items,
    }


if __name__ == "__main__":
    sys.exit(main())
