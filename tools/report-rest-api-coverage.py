#!/usr/bin/env python3
"""Report REST API source-inventory coverage by compatibility fixtures."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs/rust-port/generated/source-rest-routes.tsv"
DEFAULT_FIXTURES = ROOT / "tools/fixtures"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--fixtures-dir", default=str(DEFAULT_FIXTURES))
    parser.add_argument("--unified-report")
    parser.add_argument("--output")
    parser.add_argument(
        "--require-live-required-suites",
        action="store_true",
        help="fail unless a unified report is present and all required suites are ok",
    )
    parser.add_argument(
        "--allow-known-gaps",
        action="store_true",
        help="with --require-live-required-suites, tolerate known_gap_or_skipped counts while still failing missing/failed cases",
    )
    args = parser.parse_args()

    source_routes = load_source_routes(Path(args.source))
    fixture_paths = sorted(Path(args.fixtures_dir).glob("*.json"))
    fixture_routes = collect_fixture_routes(fixture_paths)
    fixture_coverage = coverage_for_routes(source_routes, fixture_routes)

    unified = None
    live_routes: list[dict[str, str]] = []
    if args.unified_report:
        unified = json.loads(Path(args.unified_report).read_text(encoding="utf-8"))
        live_fixture_paths = live_required_fixture_paths(unified)
        live_routes = collect_fixture_routes(live_fixture_paths)
    live_coverage = coverage_for_routes(source_routes, live_routes)

    errors: list[str] = []
    if args.require_live_required_suites:
        if unified is None:
            errors.append("--unified-report is required with --require-live-required-suites")
        else:
            errors.extend(unified_required_suite_errors(unified, allow_known_gaps=args.allow_known_gaps))

    report = {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "source": str(Path(args.source)),
        "fixtures_dir": str(Path(args.fixtures_dir)),
        "unified_report": args.unified_report,
        "summary": {
            "passed": not errors,
            "source_route_count": len(source_routes),
            "in_scope_source_route_count": sum(1 for route in source_routes if route["status"] != "out-of-scope"),
            "fixture_route_count": len(fixture_routes),
            "fixture_matched_source_route_count": len(fixture_coverage["matched_source_route_keys"]),
            "fixture_uncovered_in_scope_route_count": len(fixture_coverage["uncovered_in_scope_source_routes"]),
            "fixture_matched_source_route_ratio": ratio(
                len(fixture_coverage["matched_source_route_keys"]),
                sum(1 for route in source_routes if route["status"] != "out-of-scope"),
            ),
            "live_required_fixture_route_count": len(live_routes),
            "live_required_matched_source_route_count": len(live_coverage["matched_source_route_keys"]),
            "live_required_uncovered_in_scope_route_count": len(live_coverage["uncovered_in_scope_source_routes"]),
            "live_required_matched_source_route_ratio": ratio(
                len(live_coverage["matched_source_route_keys"]),
                sum(1 for route in source_routes if route["status"] != "out-of-scope"),
            ),
            "unified_required_suite_status": (
                required_suite_status(unified, allow_known_gaps=args.allow_known_gaps)
                if unified is not None
                else "missing"
            ),
            "unified_required_suite_classification": (
                required_suite_classification(unified) if unified is not None else {}
            ),
        },
        "source_status_counts": status_counts(source_routes),
        "fixture_coverage": fixture_coverage,
        "live_required_suite_coverage": live_coverage,
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["status"] == "ok" else 1


def load_source_routes(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            {
                "status": row.get("status", ""),
                "method": (row.get("method") or "").upper(),
                "path": row.get("path_or_expression") or "",
                "source": row.get("source") or "",
                "line": row.get("line") or "",
            }
            for row in csv.DictReader(handle, delimiter="\t")
        ]


def collect_fixture_routes(paths: list[Path]) -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for case in iter_fixture_cases(payload):
            method = str(case.get("method") or "").upper()
            route_path = str(case.get("path") or "")
            if method and route_path:
                routes.append({"method": method, "path": route_path, "fixture": str(path)})
    return routes


def iter_fixture_cases(value: Any):
    if isinstance(value, dict):
        for key in ("setup", "cases"):
            items = value.get(key)
            if isinstance(items, list):
                for item in items:
                    yield from iter_fixture_cases(item)
        if value.get("method") and value.get("path"):
            yield value
    elif isinstance(value, list):
        for item in value:
            yield from iter_fixture_cases(item)


def live_required_fixture_paths(report: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for suite in report.get("suite_results") or []:
        if not isinstance(suite, dict) or not suite.get("required") or suite.get("status") != "ok":
            continue
        fixture_path = suite.get("fixture_path")
        if isinstance(fixture_path, str) and fixture_path:
            paths.append(Path(fixture_path))
    return paths


def coverage_for_routes(source_routes: list[dict[str, str]], observed_routes: list[dict[str, str]]) -> dict[str, Any]:
    matched_keys: set[str] = set()
    unmatched_observed: list[dict[str, str]] = []
    for observed in observed_routes:
        matches = [
            source
            for source in source_routes
            if route_matches(source, observed)
        ]
        if matches:
            matched_keys.update(source_key(match) for match in matches)
        else:
            unmatched_observed.append(observed)

    uncovered = [
        route
        for route in source_routes
        if route["status"] != "out-of-scope" and source_key(route) not in matched_keys
    ]
    return {
        "matched_source_route_keys": sorted(matched_keys),
        "uncovered_in_scope_source_routes": uncovered,
        "uncovered_in_scope_route_groups": route_group_counts(uncovered),
        "unmatched_observed_routes": unmatched_observed,
    }


def route_matches(source: dict[str, str], observed: dict[str, str]) -> bool:
    if source["method"] and source["method"] != observed["method"]:
        return False
    source_path = normalize_path(source["path"])
    observed_path = normalize_path(observed["path"])
    if not source_path or not observed_path:
        return False
    source_parts = split_path(source_path)
    observed_parts = split_path(observed_path)
    if len(source_parts) != len(observed_parts):
        return False
    return all(source_segment_matches(expected, actual) for expected, actual in zip(source_parts, observed_parts))


def normalize_path(path: str) -> str:
    if not path.startswith("/"):
        return ""
    return urlsplit(path).path.rstrip("/") or "/"


def split_path(path: str) -> list[str]:
    if path == "/":
        return []
    return [part for part in path.strip("/").split("/") if part]


def source_segment_matches(expected: str, actual: str) -> bool:
    return (expected.startswith("{") and expected.endswith("}")) or expected == actual


def route_group_counts(routes: list[dict[str, str]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = {}
    for route in routes:
        key = (route_group(route["path"]), route["status"] or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return [
        {"group": group, "status": status, "count": count}
        for (group, status), count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0][0], item[0][1]),
        )
    ]


def route_group(path: str) -> str:
    normalized = normalize_path(path)
    if not normalized or source_path_is_dynamic_expression(path):
        return "dynamic-or-unparsed"
    parts = split_path(normalized)
    if not parts:
        return "/"
    first = parts[0]
    if first.startswith("{") and first.endswith("}"):
        if len(parts) >= 2:
            return f"/{{index}}/{parts[1]}"
        return "/{index}"
    return f"/{first}"


def source_path_is_dynamic_expression(path: str) -> bool:
    return any(token in path for token in ('"', "+", "String.format", "Locale.ROOT"))


def source_key(route: dict[str, str]) -> str:
    return f"{route['method']} {route['path']} {route['source']}:{route['line']}"


def status_counts(routes: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for route in routes:
        status = route["status"] or "unknown"
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def required_suite_status(report: dict[str, Any], *, allow_known_gaps: bool = False) -> str:
    errors = unified_required_suite_errors(report, allow_known_gaps=allow_known_gaps)
    return "ok" if not errors else "failed"


def unified_required_suite_errors(
    report: dict[str, Any],
    *,
    allow_known_gaps: bool = False,
) -> list[str]:
    errors: list[str] = []
    for suite in report.get("suite_results") or []:
        if not isinstance(suite, dict) or not suite.get("required"):
            continue
        if suite.get("status") != "ok":
            errors.append(f"{suite.get('name')}: required suite status is {suite.get('status')}")
        classification = suite.get("classification") or {}
        required_zero_keys = ("missing", "failed")
        if not allow_known_gaps:
            required_zero_keys = (*required_zero_keys, "known_gap_or_skipped")
        for key in required_zero_keys:
            if int(classification.get(key) or 0):
                errors.append(f"{suite.get('name')}: {key}={classification.get(key)}")
    return errors


def required_suite_classification(report: dict[str, Any]) -> dict[str, int]:
    totals = {
        "canonical_equal": 0,
        "strict_equal": 0,
        "semantic_equal": 0,
        "steelsearch_fail_closed": 0,
        "steelsearch_only": 0,
        "missing": 0,
        "failed": 0,
        "known_gap_or_skipped": 0,
        "passed": 0,
        "total_equal": 0,
    }
    for suite in report.get("suite_results") or []:
        if not isinstance(suite, dict) or not suite.get("required"):
            continue
        classification = suite.get("classification") or {}
        for key in totals:
            if key == "total_equal":
                continue
            totals[key] += int(classification.get(key) or 0)
    totals["total_equal"] = (
        totals["canonical_equal"]
        + totals["strict_equal"]
        + totals["semantic_equal"]
        + totals["steelsearch_fail_closed"]
    )
    return totals


if __name__ == "__main__":
    sys.exit(main())
