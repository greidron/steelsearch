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
SUITE_STATUS_VALUES = {"ok", "missing", "blocked", "failed"}
REPORT_SOURCES = {
    "missing",
    "output-dir",
    "output-dir+merged",
    "target",
    "target+merged",
    "target-recursive",
    "target-recursive+merged",
}
SUMMARY_KEYS = ("passed", "failed", "skipped")
CLASSIFICATION_KEYS = (
    "strict_equal",
    "canonical_equal",
    "semantic_equal",
    "steelsearch_fail_closed",
    "steelsearch_only",
    "known_gap_or_skipped",
    "failed",
    "missing",
)
CASE_GAP_KEYS = ("missing", "extra", "failed", "skipped")
SUITE_REQUIRED_FIELDS = (
    "name",
    "area",
    "parity_section",
    "required",
    "fixture_case_count",
    "status",
    "summary",
    "has_opensearch_target",
    "classification",
    "case_gaps",
    "report_source",
    "report_path",
    "fixture_path",
    "rerun",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--allow-blocked", action="store_true")
    parser.add_argument(
        "--require-no-skips",
        action="store_true",
        help="fail when required suites contain skipped fixture cases",
    )
    parser.add_argument(
        "--require-no-unresolved-skips",
        action="store_true",
        help="fail when required-suite skips are not covered by another suite in case_gap_resolution",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = validate_report(
        report,
        allow_missing=args.allow_missing,
        allow_blocked=args.allow_blocked,
        require_no_skips=args.require_no_skips,
        require_no_unresolved_skips=args.require_no_unresolved_skips,
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
    allow_blocked: bool = False,
    require_no_skips: bool = False,
    require_no_unresolved_skips: bool = False,
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
    if report.get("status") == "blocked" and not allow_blocked:
        errors.append("report has blocked or failed suite evidence")
    if require_no_unresolved_skips:
        unresolved = (
            ((report.get("coverage_summary") or {}).get("case_gap_resolution") or {})
            .get("skipped", {})
            .get("unresolved")
            or []
        )
        if unresolved:
            unresolved_names = ", ".join(
                f"{entry.get('suite')}:{entry.get('case')}"
                for entry in unresolved
                if isinstance(entry, dict)
            )
            errors.append(f"unresolved skipped fixture cases: {unresolved_names}")

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
            numeric_value = non_negative_int_or_none(value)
            if numeric_value is None:
                continue
            recomputed[key] = recomputed.get(key, 0) + numeric_value
    if classification != recomputed:
        errors.append("case_classification drift")

    seen = set()
    for suite in suites:
        name = suite.get("name")
        if not name:
            errors.append("suite without name")
            continue
        missing_fields = [field for field in SUITE_REQUIRED_FIELDS if field not in suite]
        for field in missing_fields:
            errors.append(f"{name}: missing suite field [{field}]")
        if name in seen:
            errors.append(f"duplicate suite [{name}]")
        seen.add(name)
        validate_suite_shape(name, suite, errors)
        if suite.get("status") not in SUITE_STATUS_VALUES:
            errors.append(f"{name}: invalid status [{suite.get('status')}]")
        summary_drift = suite.get("summary_drift") or {}
        if summary_drift:
            errors.append(f"{name}: suite summary drift {summary_drift}")
        case_gaps = suite.get("case_gaps") or {}
        classification = suite.get("classification") or {}
        safe_summary = suite.get("summary") if isinstance(suite.get("summary"), dict) else {}
        safe_classification = classification if isinstance(classification, dict) else {}
        safe_case_gaps = case_gaps if isinstance(case_gaps, dict) else {}
        gap_classification_keys = {
            "missing": "missing",
            "failed": "failed",
            "skipped": "known_gap_or_skipped",
        }
        for gap_key, classification_key in gap_classification_keys.items():
            classification_count = non_negative_int_or_none(safe_classification.get(classification_key)) or 0
            if gap_key in safe_case_gaps and len(safe_case_gaps.get(gap_key) or []) != classification_count:
                errors.append(f"{name}: {gap_key} case_gaps/classification drift")
        if suite.get("required") and suite.get("report_source") == "missing" and not allow_missing:
            errors.append(f"{name}: missing required report")
        if suite.get("required") and suite.get("classification", {}).get("missing", 0) and not allow_missing:
            errors.append(f"{name}: missing fixture case evidence")
        if suite.get("required") and suite.get("status") in {"failed", "blocked"}:
            errors.append(f"{name}: required suite status is {suite.get('status')}")
        if suite.get("required") and (non_negative_int_or_none(safe_summary.get("failed")) or 0):
            errors.append(f"{name}: required suite has failed cases")
        if suite.get("required") and (non_negative_int_or_none(safe_classification.get("failed")) or 0):
            errors.append(f"{name}: failed fixture case evidence")
        if suite.get("required") and require_no_skips:
            skipped = non_negative_int_or_none(safe_classification.get("known_gap_or_skipped")) or 0
            if skipped:
                errors.append(f"{name}: skipped required fixture cases")
    return errors


def validate_suite_shape(name: str, suite: dict[str, Any], errors: list[str]) -> None:
    if suite.get("parity_section") not in REQUIRED_SECTIONS:
        errors.append(f"{name}: invalid parity_section [{suite.get('parity_section')}]")
    if not isinstance(suite.get("area"), str) or not suite.get("area"):
        errors.append(f"{name}: invalid area")
    if not isinstance(suite.get("required"), bool):
        errors.append(f"{name}: required must be boolean")
    if not isinstance(suite.get("has_opensearch_target"), bool):
        errors.append(f"{name}: has_opensearch_target must be boolean")
    if not isinstance(suite.get("fixture_case_count"), int) or suite.get("fixture_case_count", -1) < 0:
        errors.append(f"{name}: fixture_case_count must be a non-negative integer")
    if suite.get("report_source") not in REPORT_SOURCES:
        errors.append(f"{name}: invalid report_source [{suite.get('report_source')}]")
    if not isinstance(suite.get("report_path"), str) or not suite.get("report_path"):
        errors.append(f"{name}: invalid report_path")
    if not isinstance(suite.get("fixture_path"), str) or not suite.get("fixture_path"):
        errors.append(f"{name}: invalid fixture_path")

    summary = suite.get("summary")
    if not isinstance(summary, dict):
        errors.append(f"{name}: summary must be an object")
    else:
        for key in SUMMARY_KEYS:
            validate_non_negative_int(name, f"summary.{key}", summary.get(key), errors)

    classification = suite.get("classification")
    if not isinstance(classification, dict):
        errors.append(f"{name}: classification must be an object")
    else:
        for key in CLASSIFICATION_KEYS:
            validate_non_negative_int(name, f"classification.{key}", classification.get(key), errors)

    case_gaps = suite.get("case_gaps")
    if not isinstance(case_gaps, dict):
        errors.append(f"{name}: case_gaps must be an object")
    else:
        for key in CASE_GAP_KEYS:
            if not isinstance(case_gaps.get(key), list):
                errors.append(f"{name}: case_gaps.{key} must be a list")

    rerun = suite.get("rerun")
    if not isinstance(rerun, dict):
        errors.append(f"{name}: rerun must be an object")
    else:
        for key in ("unified_command", "direct_command"):
            if not isinstance(rerun.get(key), str):
                errors.append(f"{name}: rerun.{key} must be a string")


def validate_non_negative_int(name: str, field: str, value: Any, errors: list[str]) -> None:
    if non_negative_int_or_none(value) is None:
        errors.append(f"{name}: {field} must be a non-negative integer")


def non_negative_int_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


if __name__ == "__main__":
    raise SystemExit(main())
