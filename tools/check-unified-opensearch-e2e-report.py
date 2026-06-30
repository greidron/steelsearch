#!/usr/bin/env python3
"""Validate a unified Steelsearch/OpenSearch E2E comparison report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_SECTIONS = {
    "route_parity",
    "semantic_parity",
    "durability_parity",
    "security_parity",
    "distributed_parity",
}
STATUS_VALUES = {"ok", "missing", "blocked"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument(
        "--require-no-skips",
        action="store_true",
        help="fail when required suites contain skipped fixture cases",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = validate_report(
        report,
        allow_missing=args.allow_missing,
        require_no_skips=args.require_no_skips,
    )
    if errors:
        for error in errors:
            print(f"unified E2E report assertion failed: {error}")
        return 1
    print(
        json.dumps(
            {
                "report": str(Path(args.report)),
                "status": report["status"],
                "suite_count": report["coverage_summary"]["suite_count"],
                "reported_suite_count": report["coverage_summary"]["reported_suite_count"],
                "opensearch_compared_suite_count": report["coverage_summary"]["opensearch_compared_suite_count"],
                "summary": {"passed": True},
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def validate_report(
    report: dict[str, Any],
    allow_missing: bool,
    require_no_skips: bool = False,
) -> list[str]:
    errors: list[str] = []
    for field in ("profile", "generated_at", "status", "coverage_summary", "suite_results"):
        if field not in report:
            errors.append(f"missing top-level field [{field}]")
    for section in REQUIRED_SECTIONS:
        if section not in report:
            errors.append(f"missing parity section [{section}]")
            continue
        section_payload = report[section]
        for field in ("required_suites", "report_paths", "status"):
            if field not in section_payload:
                errors.append(f"{section}: missing field [{field}]")
        if section_payload.get("status") not in STATUS_VALUES:
            errors.append(f"{section}: invalid status [{section_payload.get('status')}]")

    if report.get("status") not in STATUS_VALUES:
        errors.append(f"invalid top-level status [{report.get('status')}]")
    if report.get("status") == "missing" and not allow_missing:
        errors.append("report has missing required suite evidence")
    if report.get("status") == "blocked":
        errors.append("report has failed required suite evidence")

    suites = report.get("suite_results") or []
    summary = report.get("coverage_summary") or {}
    if summary.get("suite_count") != len(suites):
        errors.append("suite_count does not match suite_results length")
    if summary.get("required_suite_count") != sum(1 for suite in suites if suite.get("required")):
        errors.append("required_suite_count drift")
    if summary.get("reported_suite_count") != sum(1 for suite in suites if suite.get("report_source") != "missing"):
        errors.append("reported_suite_count drift")
    if summary.get("opensearch_compared_suite_count") != sum(1 for suite in suites if suite.get("has_opensearch_target")):
        errors.append("opensearch_compared_suite_count drift")

    classification = summary.get("case_classification") or {}
    recomputed: dict[str, int] = {}
    for suite in suites:
        for key, value in (suite.get("classification") or {}).items():
            recomputed[key] = recomputed.get(key, 0) + int(value)
    if classification != recomputed:
        errors.append("case_classification drift")

    seen = set()
    for suite in suites:
        name = suite.get("name")
        if not name:
            errors.append("suite without name")
            continue
        if name in seen:
            errors.append(f"duplicate suite [{name}]")
        seen.add(name)
        if suite.get("status") not in {"ok", "missing", "blocked", "failed"}:
            errors.append(f"{name}: invalid status [{suite.get('status')}]")
        summary_drift = suite.get("summary_drift") or {}
        if summary_drift:
            errors.append(f"{name}: suite summary drift {summary_drift}")
        case_gaps = suite.get("case_gaps") or {}
        classification = suite.get("classification") or {}
        gap_classification_keys = {
            "missing": "missing",
            "failed": "failed",
            "skipped": "known_gap_or_skipped",
        }
        for gap_key, classification_key in gap_classification_keys.items():
            if gap_key in case_gaps and len(case_gaps.get(gap_key) or []) != int(classification.get(classification_key) or 0):
                errors.append(f"{name}: {gap_key} case_gaps/classification drift")
        if suite.get("required") and suite.get("report_source") == "missing" and not allow_missing:
            errors.append(f"{name}: missing required report")
        if suite.get("required") and suite.get("classification", {}).get("missing", 0) and not allow_missing:
            errors.append(f"{name}: missing fixture case evidence")
        if suite.get("required") and suite.get("status") in {"failed", "blocked"}:
            errors.append(f"{name}: required suite status is {suite.get('status')}")
        if suite.get("required") and int(suite.get("summary", {}).get("failed") or 0):
            errors.append(f"{name}: required suite has failed cases")
        if suite.get("required") and int(suite.get("classification", {}).get("failed") or 0):
            errors.append(f"{name}: failed fixture case evidence")
        if suite.get("required") and require_no_skips:
            skipped = int(suite.get("classification", {}).get("known_gap_or_skipped") or 0)
            if skipped:
                errors.append(f"{name}: skipped required fixture cases")
    return errors


if __name__ == "__main__":
    raise SystemExit(main())
