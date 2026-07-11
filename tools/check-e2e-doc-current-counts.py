#!/usr/bin/env python3
"""Fail if current E2E/REST documentation counts drift from reports."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BROAD_REPORT = (
    ROOT / "target/unified-opensearch-e2e-broad-current/unified-opensearch-e2e-report.json"
)
DEFAULT_REST_REPORT = ROOT / "target/rest-api-coverage-current-check.json"
DEFAULT_TRANSPORT_REPORT = ROOT / "target/transport-action-coverage-current-check.json"
DEFAULT_GAP_DOC = ROOT / "docs/rust-port/opensearch-e2e-gap-inventory.md"
DEFAULT_PERF_DOC = ROOT / "docs/rust-port/production-performance-validation.md"
DEFAULT_HANDOFF_DOC = ROOT / "docs/rust-port/search-benchmark-handoff.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_int(pattern: str, text: str, label: str) -> int:
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f"{label}: pattern not found")
    for value in match.groups():
        if value is not None:
            return int(value)
    raise ValueError(f"{label}: pattern did not capture an integer")


def find_tuple(pattern: str, text: str, label: str) -> tuple[int, ...]:
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f"{label}: pattern not found")
    return tuple(int(value) for value in match.groups())


def suite_summary(report: dict[str, Any], name: str) -> dict[str, int]:
    for suite in report.get("suite_results", []):
        if suite.get("name") == name:
            summary = suite.get("summary")
            if not isinstance(summary, dict):
                raise ValueError(f"{name}: summary missing")
            return {
                "passed": int(summary.get("passed", 0)),
                "failed": int(summary.get("failed", 0)),
                "skipped": int(summary.get("skipped", 0)),
            }
    raise ValueError(f"{name}: suite missing")


def effective_classification(report: dict[str, Any]) -> dict[str, int]:
    summary = report.get("coverage_summary")
    if not isinstance(summary, dict):
        raise ValueError("coverage_summary missing")
    effective = summary.get("effective_case_classification")
    if not isinstance(effective, dict):
        raise ValueError("coverage_summary.effective_case_classification missing")
    return {key: int(effective.get(key, 0)) for key in (
        "canonical_equal",
        "strict_equal",
        "semantic_equal",
        "steelsearch_only",
        "known_gap_or_skipped",
        "failed",
        "missing",
    )}


def skipped_resolution(report: dict[str, Any]) -> dict[str, int]:
    summary = report.get("coverage_summary")
    if not isinstance(summary, dict):
        raise ValueError("coverage_summary missing")
    resolution = summary.get("case_gap_resolution", {}).get("skipped")
    if not isinstance(resolution, dict):
        raise ValueError("coverage_summary.case_gap_resolution.skipped missing")
    return {
        "total_count": int(resolution.get("total_count", 0)),
        "resolved_by_other_suite_count": int(
            resolution.get("resolved_by_other_suite_count", 0)
        ),
        "unresolved_count": int(resolution.get("unresolved_count", 0)),
    }


def rest_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("REST coverage summary missing")
    return summary


def transport_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("transport coverage summary missing")
    return summary


def expect_equal(errors: list[str], label: str, documented: int, actual: int) -> None:
    if documented != actual:
        errors.append(f"{label}: documented {documented}, report {actual}")


def validate(
    *,
    broad_report: dict[str, Any],
    rest_report: dict[str, Any],
    transport_report: dict[str, Any],
    gap_doc: str,
    performance_doc: str,
    handoff_doc: str,
) -> dict[str, Any]:
    errors: list[str] = []

    for suite_name in ("search-compat", "search-strict", "search-semantic"):
        try:
            documented = find_tuple(
                rf"- `{re.escape(suite_name)}`: (\d+) passed, 0 failed, (\d+) skipped\.",
                gap_doc,
                f"{suite_name} documented summary",
            )
            actual = suite_summary(broad_report, suite_name)
            expect_equal(errors, f"{suite_name}.passed", documented[0], actual["passed"])
            expect_equal(errors, f"{suite_name}.failed", 0, actual["failed"])
            expect_equal(errors, f"{suite_name}.skipped", documented[1], actual["skipped"])
        except ValueError as exc:
            errors.append(str(exc))

    try:
        effective = effective_classification(broad_report)
        for key in (
            "canonical_equal",
            "strict_equal",
            "semantic_equal",
            "steelsearch_only",
            "known_gap_or_skipped",
            "failed",
            "missing",
        ):
            documented = find_int(
                rf"`{key}=(\d+)`|{key}=(\d+)",
                gap_doc,
                f"gap doc {key}",
            )
            expect_equal(errors, f"gap doc effective {key}", documented, effective[key])
    except ValueError as exc:
        errors.append(str(exc))

    try:
        skip = skipped_resolution(broad_report)
        documented_raw = find_int(
            r"all (\d+) raw skipped cases are covered by other\s+required suites",
            gap_doc,
            "gap doc raw skipped cases",
        )
        expect_equal(errors, "gap doc raw skipped cases", documented_raw, skip["total_count"])
        expect_equal(errors, "broad unresolved skipped cases", 0, skip["unresolved_count"])
    except ValueError as exc:
        errors.append(str(exc))

    try:
        rest = rest_summary(rest_report)
        fixture_matched, fixture_total = find_tuple(
            r"REST source inventory fixture coverage \| `(\d+)/(\d+)` in-scope source routes matched by fixtures",
            gap_doc,
            "gap doc REST fixture source coverage",
        )
        expect_equal(
            errors,
            "gap doc REST fixture matched source routes",
            fixture_matched,
            int(rest["fixture_matched_source_route_count"]),
        )
        expect_equal(
            errors,
            "gap doc REST fixture source route denominator",
            fixture_total,
            int(rest["in_scope_source_route_count"]),
        )

        live_matched, live_total, live_fixture_routes, steelsearch_only = find_tuple(
            r"REST live-required source-route mapping \| `(\d+)/(\d+)` in-scope source routes matched by live-required fixture routes, with `(\d+)` live-required fixture routes and `(\d+)` required-suite Steelsearch-only cases",
            gap_doc,
            "gap doc REST live-required source coverage",
        )
        expect_equal(
            errors,
            "gap doc REST live-required matched source routes",
            live_matched,
            int(rest["live_required_matched_source_route_count"]),
        )
        expect_equal(
            errors,
            "gap doc REST live-required source route denominator",
            live_total,
            int(rest["in_scope_source_route_count"]),
        )
        expect_equal(
            errors,
            "gap doc REST live-required fixture route count",
            live_fixture_routes,
            int(rest["live_required_fixture_route_count"]),
        )
        steelsearch_only_summary = rest["unified_required_suite_steelsearch_only_summary"]
        expect_equal(
            errors,
            "gap doc REST required-suite Steelsearch-only cases",
            steelsearch_only,
            int(steelsearch_only_summary["effective_total"]),
        )

        implemented, out_of_scope = find_tuple(
            r"REST source statuses \| `implemented=(\d+)`, `out-of-scope=(\d+)`",
            gap_doc,
            "gap doc REST source statuses",
        )
        status_counts = rest_report.get("source_status_counts", {})
        expect_equal(errors, "gap doc REST implemented rows", implemented, int(status_counts.get("implemented", 0)))
        expect_equal(errors, "gap doc REST out-of-scope rows", out_of_scope, int(status_counts.get("out-of-scope", 0)))
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))

    try:
        transport = transport_summary(transport_report)
        accepted_rows, release_matched, release_total = find_tuple(
            r"Transport source inventory \| `(\d+)` accepted transport evidence rows plus `(\d+)/(\d+)` source-derived actions with release-parity runtime evidence",
            gap_doc,
            "gap doc transport source inventory",
        )
        expect_equal(
            errors,
            "gap doc accepted transport evidence rows",
            accepted_rows,
            int(transport["accepted_evidence_action_count"]),
        )
        expect_equal(
            errors,
            "gap doc transport release matched source actions",
            release_matched,
            int(transport["release_parity_source_matched_action_count"]),
        )
        expect_equal(
            errors,
            "gap doc transport source action denominator",
            release_total,
            int(transport["transport_action_count"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))

    try:
        rest = rest_summary(rest_report)
        source_total, in_scope, implemented, out_of_scope = find_tuple(
            r"source REST inventory: (\d+) total rows, (\d+) in scope, with (\d+)\s+`implemented` and (\d+) `out-of-scope` rows",
            performance_doc,
            "performance doc source REST inventory",
        )
        expect_equal(errors, "REST source_route_count", source_total, int(rest["source_route_count"]))
        expect_equal(
            errors,
            "REST in_scope_source_route_count",
            in_scope,
            int(rest["in_scope_source_route_count"]),
        )
        status_counts = rest_report.get("source_status_counts", {})
        expect_equal(errors, "REST implemented rows", implemented, int(status_counts.get("implemented", 0)))
        expect_equal(errors, "REST out-of-scope rows", out_of_scope, int(status_counts.get("out-of-scope", 0)))

        fixture_matched, fixture_total = find_tuple(
            r"all repo compatibility fixtures touch (\d+) of the (\d+) in-scope source route\s+rows",
            performance_doc,
            "performance doc fixture coverage",
        )
        expect_equal(
            errors,
            "REST fixture matched source routes",
            fixture_matched,
            int(rest["fixture_matched_source_route_count"]),
        )
        expect_equal(
            errors,
            "REST fixture coverage denominator",
            fixture_total,
            int(rest["in_scope_source_route_count"]),
        )

        live_matched = find_int(
            r"that broader report now touches all (\d+) in-scope source route rows",
            performance_doc,
            "performance doc live-required coverage",
        )
        expect_equal(
            errors,
            "REST live-required matched source routes",
            live_matched,
            int(rest["live_required_matched_source_route_count"]),
        )

        raw_skips = find_int(
            r"broader report still records (\d+) fixture-classified known gap or skipped\s+cases",
            performance_doc,
            "performance doc raw known gap or skipped cases",
        )
        resolved_skips = find_int(
            r"all (\d+) are resolved by dedicated suites",
            performance_doc,
            "performance doc resolved skips",
        )
        rest_skip = rest["unified_required_suite_skip_resolution"]
        expect_equal(errors, "REST raw skipped cases", raw_skips, int(rest_skip["total_count"]))
        expect_equal(
            errors,
            "REST resolved skipped cases",
            resolved_skips,
            int(rest_skip["resolved_by_other_suite_count"]),
        )
        expect_equal(errors, "REST unresolved skipped cases", 0, int(rest_skip["unresolved_count"]))
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))

    for suite_name in ("search-compat", "search-strict", "search-semantic"):
        try:
            documented = find_tuple(
                rf"- `{re.escape(suite_name)}`: `?(\d+)`? passed, `?0`? failed, `?(\d+)`? skipped\.",
                handoff_doc,
                f"handoff {suite_name} documented summary",
            )
            actual = suite_summary(broad_report, suite_name)
            expect_equal(errors, f"handoff {suite_name}.passed", documented[0], actual["passed"])
            expect_equal(errors, f"handoff {suite_name}.failed", 0, actual["failed"])
            expect_equal(errors, f"handoff {suite_name}.skipped", documented[1], actual["skipped"])
        except ValueError as exc:
            errors.append(str(exc))

    try:
        effective = effective_classification(broad_report)
        for key in (
            "canonical_equal",
            "strict_equal",
            "semantic_equal",
            "steelsearch_only",
            "known_gap_or_skipped",
            "failed",
            "missing",
        ):
            documented = find_int(
                rf"`{key}=(\d+)`|{key}=(\d+)",
                handoff_doc,
                f"handoff {key}",
            )
            expect_equal(errors, f"handoff effective {key}", documented, effective[key])
    except ValueError as exc:
        errors.append(str(exc))

    return {
        "status": "failed" if errors else "ok",
        "errors": errors,
        "summary": {
            "checked_documents": 3,
            "checked_suites": ["search-compat", "search-strict", "search-semantic"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broad-report", type=Path, default=DEFAULT_BROAD_REPORT)
    parser.add_argument("--rest-report", type=Path, default=DEFAULT_REST_REPORT)
    parser.add_argument("--transport-report", type=Path, default=DEFAULT_TRANSPORT_REPORT)
    parser.add_argument("--gap-doc", type=Path, default=DEFAULT_GAP_DOC)
    parser.add_argument("--performance-doc", type=Path, default=DEFAULT_PERF_DOC)
    parser.add_argument("--handoff-doc", type=Path, default=DEFAULT_HANDOFF_DOC)
    args = parser.parse_args()

    result = validate(
        broad_report=load_json(args.broad_report),
        rest_report=load_json(args.rest_report),
        transport_report=load_json(args.transport_report),
        gap_doc=args.gap_doc.read_text(encoding="utf-8"),
        performance_doc=args.performance_doc.read_text(encoding="utf-8"),
        handoff_doc=args.handoff_doc.read_text(encoding="utf-8"),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
