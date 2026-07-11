#!/usr/bin/env python3
"""Validate a unified Steelsearch/OpenSearch E2E comparison report."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
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
CASE_GAP_KEYS = ("missing", "extra", "failed", "skipped", "fail_closed")
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
    parser.add_argument(
        "--require-section",
        action="append",
        choices=sorted(REQUIRED_SECTIONS),
        default=[],
        help="fail when the named parity section has no required suites; may be repeated",
    )
    parser.add_argument(
        "--require-opensearch-suite",
        action="append",
        default=[],
        help="fail when the named suite lacks OpenSearch comparison evidence; may be repeated",
    )
    parser.add_argument(
        "--max-report-age-seconds",
        type=float,
        help="fail if the unified report is older than this many seconds",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path = Path(args.report)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    errors = validate_report(
        report,
        allow_missing=args.allow_missing,
        allow_blocked=args.allow_blocked,
        require_no_skips=args.require_no_skips,
        require_no_unresolved_skips=args.require_no_unresolved_skips,
        required_nonempty_sections=set(args.require_section),
        required_opensearch_suites=set(args.require_opensearch_suite),
    )
    freshness = report_fresh(report_path, args.max_report_age_seconds)
    if not freshness["fresh"]:
        errors.append(freshness["reason"])
    if errors:
        for error in errors:
            print(f"unified E2E report assertion failed: {error}")
        return 1
    section_summary = parity_section_summary(report)
    classification_summary = output_classification_summary(report)
    print(
        json.dumps(
            {
                "report": str(report_path),
                "status": report["status"],
                "report_age_seconds": freshness["age_seconds"],
                "report_max_age_seconds": freshness["max_age_seconds"],
                "suite_count": report["coverage_summary"]["suite_count"],
                "reported_suite_count": report["coverage_summary"]["reported_suite_count"],
                "opensearch_compared_suite_count": report["coverage_summary"]["opensearch_compared_suite_count"],
                "summary": {
                    "passed": True,
                    "required_sections": sorted(args.require_section),
                    "required_section_count": len(set(args.require_section)),
                    "required_section_suite_counts": section_summary["suite_counts"],
                    "required_section_report_path_counts": section_summary["report_path_counts"],
                    **classification_summary,
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def report_fresh(path: Path, max_age_seconds: float | None) -> dict[str, Any]:
    if max_age_seconds is None:
        return {
            "fresh": True,
            "age_seconds": None,
            "max_age_seconds": None,
            "reason": "",
        }
    if not path.is_file():
        return {
            "fresh": False,
            "age_seconds": None,
            "max_age_seconds": max_age_seconds,
            "reason": f"report is missing: {path}",
        }
    age_seconds = max(0.0, time.time() - path.stat().st_mtime)
    fresh = age_seconds <= max_age_seconds
    return {
        "fresh": fresh,
        "age_seconds": age_seconds,
        "max_age_seconds": max_age_seconds,
        "reason": (
            ""
            if fresh
            else f"report is stale: age_seconds={age_seconds:.3f} max_report_age_seconds={max_age_seconds:g}"
        ),
    }


def validate_report(
    report: dict[str, Any],
    allow_missing: bool,
    allow_blocked: bool = False,
    require_no_skips: bool = False,
    require_no_unresolved_skips: bool = False,
    required_nonempty_sections: set[str] | None = None,
    required_opensearch_suites: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    required_nonempty_sections = required_nonempty_sections or set()
    required_opensearch_suites = required_opensearch_suites or set()
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
        if section in required_nonempty_sections and not section_payload.get("required_suites"):
            errors.append(f"{section}: no required suites")

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
    seen_suite_names = {str(suite.get("name")) for suite in suites if suite.get("name")}
    for suite_name in sorted(required_opensearch_suites):
        if suite_name not in seen_suite_names:
            errors.append(f"{suite_name}: required OpenSearch suite is missing")
            continue
        suite = next(suite for suite in suites if str(suite.get("name")) == suite_name)
        if suite.get("has_opensearch_target") is not True:
            errors.append(f"{suite_name}: required OpenSearch comparison evidence is missing")
    summary = report.get("coverage_summary") or {}
    if summary.get("suite_count") != len(suites):
        errors.append("suite_count does not match suite_results length")
    if summary.get("required_suite_count") != sum(1 for suite in suites if suite.get("required")):
        errors.append("required_suite_count drift")
    if summary.get("reported_suite_count") != sum(1 for suite in suites if suite.get("report_source") != "missing"):
        errors.append("reported_suite_count drift")
    if summary.get("opensearch_compared_suite_count") != sum(1 for suite in suites if suite.get("has_opensearch_target")):
        errors.append("opensearch_compared_suite_count drift")
    validate_parity_section_inventory(report, suites, errors)

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
    validate_case_gap_resolution(summary, suites, errors)

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
        validate_fixture_backed_classification(name, suite, errors)
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
            "fail_closed": "steelsearch_fail_closed",
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


def validate_parity_section_inventory(
    report: dict[str, Any],
    suites: list[dict[str, Any]],
    errors: list[str],
) -> None:
    required_suite_names_by_section: dict[str, list[str]] = {
        section: [] for section in REQUIRED_SECTIONS
    }
    report_paths_by_section: dict[str, list[str]] = {
        section: [] for section in REQUIRED_SECTIONS
    }
    for suite in suites:
        section = suite.get("parity_section")
        if section not in REQUIRED_SECTIONS or suite.get("required") is not True:
            continue
        required_suite_names_by_section[str(section)].append(str(suite.get("name") or ""))
        report_paths_by_section[str(section)].append(str(suite.get("report_path") or ""))

    for section in REQUIRED_SECTIONS:
        section_payload = report.get(section)
        if not isinstance(section_payload, dict):
            continue
        reported_required_suites = section_payload.get("required_suites")
        reported_paths = section_payload.get("report_paths")
        if not isinstance(reported_required_suites, list):
            errors.append(f"{section}: required_suites must be a list")
            continue
        if not isinstance(reported_paths, list):
            errors.append(f"{section}: report_paths must be a list")
            continue
        expected_suites = sorted(required_suite_names_by_section[section])
        expected_paths = sorted(report_paths_by_section[section])
        actual_suites = sorted(str(value) for value in reported_required_suites)
        actual_paths = sorted(str(value) for value in reported_paths)
        if actual_suites != expected_suites:
            errors.append(f"{section}: required_suites drift from suite_results")
        if actual_paths != expected_paths:
            errors.append(f"{section}: report_paths drift from suite_results")


def parity_section_summary(report: dict[str, Any]) -> dict[str, dict[str, int]]:
    suite_counts: dict[str, int] = {}
    report_path_counts: dict[str, int] = {}
    for section in sorted(REQUIRED_SECTIONS):
        section_payload = report.get(section)
        if not isinstance(section_payload, dict):
            suite_counts[section] = 0
            report_path_counts[section] = 0
            continue
        required_suites = section_payload.get("required_suites")
        report_paths = section_payload.get("report_paths")
        suite_counts[section] = len(required_suites) if isinstance(required_suites, list) else 0
        report_path_counts[section] = len(report_paths) if isinstance(report_paths, list) else 0
    return {
        "suite_counts": suite_counts,
        "report_path_counts": report_path_counts,
    }


def output_classification_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("coverage_summary")
    if not isinstance(summary, dict):
        summary = {}
    gap_resolution = summary.get("case_gap_resolution")
    if not isinstance(gap_resolution, dict):
        gap_resolution = {}
    skipped = gap_resolution.get("skipped")
    if not isinstance(skipped, dict):
        skipped = {}
    return {
        "case_classification": dict_or_empty(summary.get("case_classification")),
        "effective_case_classification": dict_or_empty(
            summary.get("effective_case_classification")
        ),
        "skipped_case_resolution": {
            "total_count": int_or_zero(skipped.get("total_count")),
            "resolved_by_other_suite_count": int_or_zero(
                skipped.get("resolved_by_other_suite_count")
            ),
            "unresolved_count": int_or_zero(skipped.get("unresolved_count")),
        },
    }


def validate_case_gap_resolution(
    summary: dict[str, Any],
    suites: list[dict[str, Any]],
    errors: list[str],
) -> None:
    resolution = summary.get("case_gap_resolution")
    if not isinstance(resolution, dict):
        errors.append("case_gap_resolution missing or invalid")
        return
    skipped_resolution = resolution.get("skipped")
    if not isinstance(skipped_resolution, dict):
        errors.append("case_gap_resolution.skipped missing or invalid")
        return

    skipped_entries: list[tuple[str, str]] = []
    required_suites_by_name: dict[str, dict[str, Any]] = {}
    passed_cases_by_suite: dict[str, set[str]] = {}
    for suite in suites:
        if not suite.get("required"):
            continue
        suite_name = str(suite.get("name"))
        required_suites_by_name[suite_name] = suite
        passed_cases = suite.get("passed_cases")
        if isinstance(passed_cases, list):
            passed_cases_by_suite[suite_name] = {
                str(case_name) for case_name in passed_cases
            }
        skipped_cases = (suite.get("case_gaps") or {}).get("skipped") or []
        if isinstance(skipped_cases, list):
            skipped_entries.extend((suite_name, str(case_name)) for case_name in skipped_cases)

    resolved = skipped_resolution.get("resolved")
    unresolved = skipped_resolution.get("unresolved")
    if not isinstance(resolved, list):
        errors.append("case_gap_resolution.skipped.resolved must be a list")
        resolved = []
    if not isinstance(unresolved, list):
        errors.append("case_gap_resolution.skipped.unresolved must be a list")
        unresolved = []

    resolved_entries: list[tuple[str, str]] = []
    unresolved_entries: list[tuple[str, str]] = []
    for entry in resolved:
        parsed = parse_gap_resolution_entry("resolved", entry, errors)
        if parsed is None:
            continue
        suite_name, case_name = parsed
        resolved_entries.append(parsed)
        covered_by = entry.get("covered_by") if isinstance(entry, dict) else None
        if not isinstance(covered_by, list) or not covered_by:
            errors.append(f"{suite_name}:{case_name}: resolved skip missing covered_by")
            continue
        for covering_suite in covered_by:
            if not isinstance(covering_suite, str):
                errors.append(f"{suite_name}:{case_name}: covered_by entries must be strings")
                continue
            if covering_suite == suite_name:
                errors.append(f"{suite_name}:{case_name}: skip cannot be covered by the same suite")
                continue
            if covering_suite not in required_suites_by_name:
                errors.append(
                    f"{suite_name}:{case_name}: covering suite {covering_suite} is not a required suite"
                )
                continue
            if case_name not in passed_cases_by_suite.get(covering_suite, set()):
                errors.append(
                    f"{suite_name}:{case_name}: covering suite {covering_suite} did not pass the case"
                )
    for entry in unresolved:
        parsed = parse_gap_resolution_entry("unresolved", entry, errors)
        if parsed is not None:
            unresolved_entries.append(parsed)

    if skipped_resolution.get("total_count") != len(skipped_entries):
        errors.append("case_gap_resolution.skipped.total_count drift")
    if skipped_resolution.get("resolved_by_other_suite_count") != len(resolved_entries):
        errors.append("case_gap_resolution.skipped.resolved_by_other_suite_count drift")
    if skipped_resolution.get("unresolved_count") != len(unresolved_entries):
        errors.append("case_gap_resolution.skipped.unresolved_count drift")

    actual_entries = sorted(skipped_entries)
    reported_entries = sorted(resolved_entries + unresolved_entries)
    if reported_entries != actual_entries:
        errors.append("case_gap_resolution.skipped entries drift from suite skipped case gaps")

    classification = summary.get("case_classification")
    effective = summary.get("effective_case_classification")
    if isinstance(classification, dict) and isinstance(effective, dict):
        expected_effective = dict(classification)
        known_gap_count = non_negative_int_or_none(
            expected_effective.get("known_gap_or_skipped")
        ) or 0
        expected_effective["known_gap_or_skipped"] = max(
            0,
            known_gap_count - len(resolved_entries),
        )
        if effective != expected_effective:
            errors.append("effective_case_classification drift")
    else:
        errors.append("effective_case_classification missing or invalid")


def parse_gap_resolution_entry(
    label: str,
    entry: Any,
    errors: list[str],
) -> tuple[str, str] | None:
    if not isinstance(entry, dict):
        errors.append(f"case_gap_resolution.skipped.{label} entries must be objects")
        return None
    suite_name = entry.get("suite")
    case_name = entry.get("case")
    if not isinstance(suite_name, str) or not suite_name:
        errors.append(f"case_gap_resolution.skipped.{label} entry missing suite")
        return None
    if not isinstance(case_name, str) or not case_name:
        errors.append(f"case_gap_resolution.skipped.{label} entry missing case")
        return None
    return suite_name, case_name


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

    classification_cases = suite.get("classification_cases")
    if classification_cases is not None:
        if not isinstance(classification_cases, dict):
            errors.append(f"{name}: classification_cases must be an object")
        else:
            for key in CLASSIFICATION_KEYS:
                case_names = classification_cases.get(key)
                if not isinstance(case_names, list):
                    errors.append(f"{name}: classification_cases.{key} must be a list")
                    continue
                if any(not isinstance(case_name, str) for case_name in case_names):
                    errors.append(f"{name}: classification_cases.{key} entries must be strings")
                if isinstance(classification, dict) and len(case_names) != classification.get(key):
                    errors.append(f"{name}: classification_cases.{key}/classification.{key} drift")

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


def validate_fixture_backed_classification(
    name: str,
    suite: dict[str, Any],
    errors: list[str],
) -> None:
    fixture_cases = load_fixture_cases(suite.get("fixture_path"))
    if fixture_cases is None:
        return
    fixture_by_name = {
        str(case.get("name")): case
        for case in fixture_cases
        if isinstance(case, dict) and case.get("name")
    }
    aggregate_case = load_fixture_aggregate_case(suite.get("fixture_path"))
    if isinstance(aggregate_case, dict) and aggregate_case.get("name"):
        fixture_by_name[str(aggregate_case["name"])] = aggregate_case
    classification_cases = suite.get("classification_cases")
    if not isinstance(classification_cases, dict):
        return

    suite_has_opensearch_target = suite.get("has_opensearch_target") is True
    for case_name in classification_cases.get("steelsearch_only") or []:
        fixture_case = fixture_by_name.get(str(case_name))
        if not isinstance(fixture_case, dict):
            errors.append(f"{name}: steelsearch_only case {case_name} missing from fixture")
            continue
        if suite_has_opensearch_target and fixture_case.get("comparison") != "steelsearch_only":
            errors.append(
                f"{name}: steelsearch_only case {case_name} is not fixture-declared steelsearch_only"
            )
        expected_status = fixture_case.get("expected_steelsearch_status")
        if fixture_case.get("comparison") == "steelsearch_only" and isinstance(expected_status, int) and expected_status >= 400:
            errors.append(
                f"{name}: steelsearch_only case {case_name} should be classified as steelsearch_fail_closed"
            )

    for case_name in classification_cases.get("steelsearch_fail_closed") or []:
        fixture_case = fixture_by_name.get(str(case_name))
        if not isinstance(fixture_case, dict):
            errors.append(
                f"{name}: steelsearch_fail_closed case {case_name} missing from fixture"
            )
            continue
        if fixture_case.get("comparison") != "steelsearch_only":
            errors.append(
                f"{name}: steelsearch_fail_closed case {case_name} is not fixture-declared steelsearch_only"
            )
        expected_status = fixture_case.get("expected_steelsearch_status")
        if not (isinstance(expected_status, int) and expected_status >= 400):
            errors.append(
                f"{name}: steelsearch_fail_closed case {case_name} is missing a fail-closed expected status"
            )


def load_fixture_cases(fixture_path: Any) -> list[dict[str, Any]] | None:
    if not isinstance(fixture_path, str) or not fixture_path:
        return None
    path = Path(fixture_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(cases, list):
        return None
    return [case for case in cases if isinstance(case, dict)]


def load_fixture_aggregate_case(fixture_path: Any) -> dict[str, Any] | None:
    if not isinstance(fixture_path, str) or not fixture_path:
        return None
    path = Path(fixture_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    aggregate_case = payload.get("aggregate_case") if isinstance(payload, dict) else None
    return aggregate_case if isinstance(aggregate_case, dict) else None


def validate_non_negative_int(name: str, field: str, value: Any, errors: list[str]) -> None:
    if non_negative_int_or_none(value) is None:
        errors.append(f"{name}: {field} must be a non-negative integer")


def non_negative_int_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def int_or_zero(value: Any) -> int:
    return value if isinstance(value, int) else 0


def dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())
