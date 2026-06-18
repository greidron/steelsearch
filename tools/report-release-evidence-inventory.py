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
            if candidate.is_file()
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
