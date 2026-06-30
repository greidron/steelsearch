#!/usr/bin/env python3
"""Verify PIT E2E cases stay active in OpenSearch comparison reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PIT_CASES = {
    "search-compat": {
        "pit_open_search",
        "pit_search",
        "pit_list_search",
        "pit_clear_search",
        "pit_search_after_close_missing_context",
        "pit_shard_doc_search_after_search",
        "pit_snapshot_after_update_delete_search",
        "msearch_pit_snapshot_after_update_delete_search",
    },
    "search-strict": {
        "pit_open_search",
        "pit_search",
        "pit_list_search",
        "pit_clear_search",
        "pit_search_after_close_missing_context",
        "pit_shard_doc_search_after_search",
        "pit_snapshot_after_update_delete_search",
    },
    "search-semantic": {
        "pit_snapshot_after_update_delete_semantic",
        "pit_search_after_close_missing_context_semantic",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("unified_report")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument(
        "--require-all-pit-passed",
        action="store_true",
        help="fail if any PIT-touching compared case is not passed",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_report_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (ROOT / path).resolve()


def case_touches_pit(case: dict[str, Any]) -> bool:
    if "pit_" in str(case.get("name") or ""):
        return True
    if str(case.get("extract") or "").startswith("pit_"):
        return True
    return request_touches_pit(case) or any(
        request_touches_pit(step) for step in case.get("steps") or []
    )


def request_touches_pit(request: dict[str, Any]) -> bool:
    path = str(request.get("path") or "")
    if "point_in_time" in path or "_cat/pit_segments" in path:
        return True
    return body_touches_pit(request.get("body"))


def body_touches_pit(value: Any) -> bool:
    if isinstance(value, dict):
        if "pit" in value or "pit_id" in value:
            return True
        return any(body_touches_pit(child) for child in value.values())
    if isinstance(value, list):
        return any(body_touches_pit(child) for child in value)
    return False


def check_unified_report(unified_report_path: Path, require_all_pit_passed: bool) -> dict[str, Any]:
    unified = load_json(unified_report_path)
    suite_results = unified.get("suite_results") or unified.get("suites") or []
    suites_by_name = {
        suite.get("name"): suite
        for suite in suite_results
        if isinstance(suite, dict) and suite.get("name") in REQUIRED_PIT_CASES
    }
    errors: list[str] = []
    suite_summaries: list[dict[str, Any]] = []

    for suite_name, required_cases in sorted(REQUIRED_PIT_CASES.items()):
        suite = suites_by_name.get(suite_name)
        if suite is None:
            errors.append(f"missing suite [{suite_name}] in unified report")
            continue
        if not suite.get("has_opensearch_target"):
            errors.append(f"suite [{suite_name}] is not an OpenSearch comparison suite")
            continue
        report_path_value = suite.get("report_path")
        if not isinstance(report_path_value, str) or not report_path_value:
            errors.append(f"suite [{suite_name}] does not include report_path")
            continue

        report_path = resolve_report_path(report_path_value)
        if not report_path.exists():
            errors.append(f"suite [{suite_name}] report does not exist: {report_path}")
            continue
        report = load_json(report_path)
        cases = [
            case
            for case in report.get("cases") or []
            if isinstance(case, dict) and case_touches_pit(case)
        ]
        cases_by_name = {
            case.get("name"): case
            for case in cases
            if isinstance(case, dict) and case.get("name")
        }
        missing_required = sorted(required_cases - set(cases_by_name))
        non_passed = sorted(
            str(case.get("name"))
            for case in cases
            if case.get("status") != "passed"
        )
        if missing_required:
            errors.append(
                f"suite [{suite_name}] is missing required PIT cases: {', '.join(missing_required)}"
            )
        if require_all_pit_passed and non_passed:
            errors.append(
                f"suite [{suite_name}] has non-passed PIT cases: {', '.join(non_passed)}"
            )
        suite_summaries.append(
            {
                "name": suite_name,
                "report_path": str(report_path),
                "pit_case_count": len(cases),
                "required_pit_case_count": len(required_cases),
                "missing_required_pit_cases": missing_required,
                "non_passed_pit_cases": non_passed,
            }
        )

    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary": {
            "passed": not errors,
            "suite_count": len(suite_summaries),
            "pit_case_count": sum(suite["pit_case_count"] for suite in suite_summaries),
            "non_passed_pit_case_count": sum(
                len(suite["non_passed_pit_cases"]) for suite in suite_summaries
            ),
        },
        "suites": suite_summaries,
    }


def main() -> int:
    args = parse_args()
    result = check_unified_report(Path(args.unified_report), args.require_all_pit_passed)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: {result['summary']}")
        for error in result["errors"]:
            print(f"error: {error}", file=sys.stderr)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
