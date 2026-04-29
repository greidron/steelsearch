#!/usr/bin/env python3
"""Validate REST compatibility fixture and generated report contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--report")
    parser.add_argument("--require-report", action="store_true")
    args = parser.parse_args()

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    errors = validate_fixture(fixture)

    if args.report:
        report_path = Path(args.report)
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            errors.extend(validate_report(fixture, report))
        elif args.require_report:
            errors.append(f"missing REST compatibility report: {report_path}")
    elif args.require_report:
        errors.append("--require-report needs --report")

    if errors:
        for error in errors:
            print(f"REST compatibility assertion failed: {error}", file=sys.stderr)
        return 1
    return 0


def validate_fixture(fixture: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    seen_names: set[str] = set()
    for case in fixture.get("cases", []):
        name = case.get("name")
        if not name:
            errors.append("case is missing name")
            continue
        if name in seen_names:
            errors.append(f"duplicate case name [{name}]")
        seen_names.add(name)

        if case.get("comparison") == "steelsearch_only":
            if "expected_steelsearch_status" not in case:
                errors.append(f"steelsearch_only case [{name}] is missing expected_steelsearch_status")
            if not case.get("skip_scope"):
                errors.append(f"steelsearch_only case [{name}] is missing skip_scope")
            if not case.get("reason"):
                errors.append(f"steelsearch_only case [{name}] is missing reason")
    return errors


def validate_report(fixture: dict[str, Any], report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    fixture_cases = {case["name"]: case for case in fixture.get("cases", [])}
    report_cases = {case.get("name"): case for case in report.get("cases", []) if case.get("name")}
    missing = sorted(set(fixture_cases) - set(report_cases))
    extra = sorted(set(report_cases) - set(fixture_cases))
    if missing:
        errors.append(f"report is missing fixture cases: {', '.join(missing)}")
    if extra:
        errors.append(f"report contains cases not declared by fixture: {', '.join(extra)}")

    setup_failures = [
        f"{step.get('target')}:{step.get('name')}"
        for step in report.get("setup", [])
        if step.get("status") == "failed"
    ]
    if setup_failures:
        errors.append(f"setup failures: {', '.join(setup_failures)}")

    failed_cases = [
        case.get("name", "<unnamed>")
        for case in report.get("cases", [])
        if case.get("status") == "failed"
    ]
    if failed_cases:
        errors.append(f"failed cases: {', '.join(failed_cases)}")

    summary = report.get("summary", {})
    counted = sum(1 for case in report.get("cases", []) if case.get("status") in {"passed", "failed", "skipped"})
    summary_total = sum(int(summary.get(key, 0)) for key in ("passed", "failed", "skipped"))
    if counted != summary_total:
        errors.append(f"summary count drift: cases={counted} summary={summary_total}")

    has_opensearch = "opensearch" in (report.get("targets") or {})
    required_skips = {
        name
        for name, case in fixture_cases.items()
        if case.get("comparison") == "steelsearch_only" and has_opensearch
    }
    actual_skips = {
        case.get("name")
        for case in report.get("cases", [])
        if case.get("status") == "skipped"
    }
    missing_required_skips = sorted(required_skips - actual_skips)
    unexpected_skips = sorted(
        name
        for name in actual_skips - required_skips
        if report_cases.get(name, {}).get("skip_scope") != "degraded-source"
    )
    if missing_required_skips or unexpected_skips:
        errors.append(
            "skip drift: required "
            f"{sorted(required_skips)} but report had {sorted(actual_skips)}"
        )

    summary_skips = {skip.get("name") for skip in summary.get("skips", [])}
    if summary_skips != actual_skips:
        errors.append(
            "summary skip list drift: expected "
            f"{sorted(actual_skips)} but summary had {sorted(summary_skips)}"
        )

    for skipped in summary.get("skips", []):
        if not skipped.get("scope") or not skipped.get("reason"):
            errors.append(f"skipped case [{skipped.get('name')}] is missing scope or reason")
    return errors


if __name__ == "__main__":
    raise SystemExit(main())
