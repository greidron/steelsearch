#!/usr/bin/env python3
"""Verify PIT E2E cases stay active in OpenSearch comparison reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
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

PIT_COMPARISON_CLASSIFICATIONS = {
    "canonical_equal",
    "strict_equal",
    "semantic_equal",
}
PIT_NON_COMPARISON_CLASSIFICATIONS = {
    "failed",
    "known_gap_or_skipped",
    "missing",
    "steelsearch_fail_closed",
    "steelsearch_only",
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
    parser.add_argument(
        "--max-report-age-seconds",
        type=float,
        help="fail if the unified report is older than this many seconds",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
            "reason": f"{path} is missing",
        }
    age_seconds = time.time() - path.stat().st_mtime
    return {
        "fresh": age_seconds <= max_age_seconds,
        "age_seconds": round(age_seconds, 3),
        "max_age_seconds": max_age_seconds,
        "reason": (
            ""
            if age_seconds <= max_age_seconds
            else f"{path} is stale: age_seconds={age_seconds:.0f} max_age_seconds={max_age_seconds:.0f}"
        ),
    }


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


def case_name_touches_pit(name: str) -> bool:
    return "pit_" in name or "point_in_time" in name or "pit" in name


def embedded_suite_cases(
    suite_name: str,
    suite: dict[str, Any],
    errors: list[str],
) -> list[dict[str, Any]] | None:
    if "passed_cases" not in suite:
        return None
    passed_cases = suite.get("passed_cases")
    case_gaps = suite.get("case_gaps")
    if not isinstance(passed_cases, list):
        errors.append(f"suite [{suite_name}] passed_cases must be a list")
        return []
    if not isinstance(case_gaps, dict):
        errors.append(f"suite [{suite_name}] case_gaps must be an object")
        return []

    cases: list[dict[str, Any]] = []
    for name in passed_cases:
        if not isinstance(name, str) or not name:
            errors.append(f"suite [{suite_name}] passed_cases entries must be non-empty strings")
            continue
        cases.append({"name": name, "status": "passed"})
    for status, gap_key in (("failed", "failed"), ("skipped", "skipped")):
        names = case_gaps.get(gap_key)
        if not isinstance(names, list):
            errors.append(f"suite [{suite_name}] case_gaps.{gap_key} must be a list")
            continue
        for name in names:
            if not isinstance(name, str) or not name:
                errors.append(
                    f"suite [{suite_name}] case_gaps.{gap_key} entries must be non-empty strings"
                )
                continue
            cases.append({"name": name, "status": status})
    return cases


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


def check_unified_report(
    unified_report_path: Path,
    require_all_pit_passed: bool,
    max_report_age_seconds: float | None = None,
) -> dict[str, Any]:
    freshness = report_fresh(unified_report_path, max_report_age_seconds)
    unified = load_json(unified_report_path)
    suite_results = unified.get("suite_results") or unified.get("suites") or []
    suites_by_name = {
        suite.get("name"): suite
        for suite in suite_results
        if isinstance(suite, dict) and suite.get("name") in REQUIRED_PIT_CASES
    }
    errors: list[str] = []
    if not freshness["fresh"]:
        errors.append(freshness["reason"])
    suite_summaries: list[dict[str, Any]] = []

    for suite_name, required_cases in sorted(REQUIRED_PIT_CASES.items()):
        suite = suites_by_name.get(suite_name)
        if suite is None:
            errors.append(f"missing suite [{suite_name}] in unified report")
            continue
        if not suite.get("has_opensearch_target"):
            errors.append(f"suite [{suite_name}] is not an OpenSearch comparison suite")
            continue
        report_path = None
        cases = embedded_suite_cases(suite_name, suite, errors)
        if cases is None:
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
        else:
            cases = [
                case
                for case in cases
                if isinstance(case.get("name"), str)
                and case_name_touches_pit(str(case.get("name")))
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
        classification_summary = required_pit_classification_summary(
            suite_name,
            suite,
            required_cases,
            errors,
        )
        suite_summaries.append(
            {
                "name": suite_name,
                "report_path": str(report_path) if report_path is not None else suite.get("report_path"),
                "pit_case_count": len(cases),
                "pit_case_names": sorted(str(name) for name in cases_by_name),
                "pit_case_name_digest": stable_name_digest(
                    f"{suite_name}:{case_name}" for case_name in cases_by_name
                ),
                "required_pit_case_count": len(required_cases),
                "required_pit_case_name_digest": stable_name_digest(
                    f"{suite_name}:{case_name}" for case_name in required_cases
                ),
                "required_pit_compared_case_count": classification_summary[
                    "compared_case_count"
                ],
                "required_pit_compared_case_names": classification_summary[
                    "comparison_cases"
                ],
                "required_pit_compared_case_name_digest": stable_name_digest(
                    f"{suite_name}:{case_name}"
                    for case_name in classification_summary["comparison_cases"]
                ),
                "missing_required_pit_cases": missing_required,
                "non_passed_pit_cases": non_passed,
                "required_pit_non_comparison_cases": classification_summary[
                    "non_comparison_cases"
                ],
            }
        )

    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary": {
            "passed": not errors,
            "suite_count": len(suite_summaries),
            "pit_case_count": sum(suite["pit_case_count"] for suite in suite_summaries),
            "pit_case_name_digest": stable_name_digest(
                f"{suite['name']}:{case_name}"
                for suite in suite_summaries
                for case_name in suite["pit_case_names"]
            ),
            "required_pit_case_count": sum(
                suite["required_pit_case_count"] for suite in suite_summaries
            ),
            "required_pit_case_name_digest": stable_name_digest(
                f"{suite_name}:{case_name}"
                for suite_name, required_cases in REQUIRED_PIT_CASES.items()
                for case_name in required_cases
            ),
            "required_pit_compared_case_count": sum(
                suite["required_pit_compared_case_count"] for suite in suite_summaries
            ),
            "required_pit_compared_case_name_digest": stable_name_digest(
                f"{suite['name']}:{case_name}"
                for suite in suite_summaries
                for case_name in suite["required_pit_compared_case_names"]
            ),
            "non_passed_pit_case_count": sum(
                len(suite["non_passed_pit_cases"]) for suite in suite_summaries
            ),
            "unified_report_fresh": freshness["fresh"],
            "unified_report_age_seconds": freshness["age_seconds"],
            "unified_report_max_age_seconds": freshness["max_age_seconds"],
        },
        "suites": suite_summaries,
    }


def required_pit_classification_summary(
    suite_name: str,
    suite: dict[str, Any],
    required_cases: set[str],
    errors: list[str],
) -> dict[str, Any]:
    classification_cases = suite.get("classification_cases")
    if not isinstance(classification_cases, dict):
        errors.append(f"suite [{suite_name}] classification_cases must be an object")
        return {
            "compared_case_count": 0,
            "comparison_cases": [],
            "non_comparison_cases": [],
        }

    comparison_cases = {
        case_name
        for key in PIT_COMPARISON_CLASSIFICATIONS
        for case_name in string_list(classification_cases.get(key))
    }
    non_comparison_by_case: dict[str, list[str]] = {}
    for key in PIT_NON_COMPARISON_CLASSIFICATIONS:
        for case_name in string_list(classification_cases.get(key)):
            if case_name in required_cases:
                non_comparison_by_case.setdefault(case_name, []).append(key)

    missing_comparison = sorted(required_cases - comparison_cases)
    if missing_comparison:
        errors.append(
            f"suite [{suite_name}] required PIT cases are not classified as OpenSearch comparisons: "
            f"{', '.join(missing_comparison)}"
        )
    if non_comparison_by_case:
        errors.append(
            f"suite [{suite_name}] required PIT cases have non-comparison classifications: "
            + ", ".join(
                f"{case}={'+'.join(sorted(labels))}"
                for case, labels in sorted(non_comparison_by_case.items())
            )
        )
    return {
        "compared_case_count": len(required_cases & comparison_cases),
        "comparison_cases": sorted(required_cases & comparison_cases),
        "non_comparison_cases": [
            {"case": case, "classifications": sorted(labels)}
            for case, labels in sorted(non_comparison_by_case.items())
        ],
    }


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def stable_name_digest(names: Any) -> str:
    encoded = json.dumps(sorted(str(name) for name in names), separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def main() -> int:
    args = parse_args()
    result = check_unified_report(
        Path(args.unified_report),
        args.require_all_pit_passed,
        args.max_report_age_seconds,
    )
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: {result['summary']}")
        for error in result["errors"]:
            print(f"error: {error}", file=sys.stderr)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
