#!/usr/bin/env python3
"""Check the native-readiness artifact bundle.

This checker is intentionally conservative. It only passes when the provided
lib-suite log proves zero failed tests, the OpenSearch/search compatibility
report is green, and the Steelsearch native-route coverage report is green.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_LIB_LOG = Path("target/os-engine-tantivy-lib-test-final-native-readiness.log")
DEFAULT_SEARCH_REPORT = Path("target/opensearch-compare/search-compat-report.json")
DEFAULT_FIXTURE_COVERAGE_REPORT = Path("target/opensearch-compare/native-route-fixture-coverage-report.json")
DEFAULT_NATIVE_ROUTE_REPORT = Path("target/opensearch-compare/native-route-coverage-report.json")

TEST_RESULT_RE = re.compile(
    r"test result:\s+(?P<status>\w+)\.\s+"
    r"(?P<passed>\d+) passed;\s+"
    r"(?P<failed>\d+) failed;\s+"
    r"(?P<ignored>\d+) ignored;"
)


def read_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text()), None
    except FileNotFoundError:
        return None, f"missing file: {path}"
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON in {path}: {exc}"


def check_lib_log(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(errors="replace")
    except FileNotFoundError:
        return {
            "path": str(path),
            "ok": False,
            "reason": "missing_lib_suite_log",
        }

    matches = list(TEST_RESULT_RE.finditer(text))
    if not matches:
        return {
            "path": str(path),
            "ok": False,
            "reason": "missing_test_result_line",
        }
    match = matches[-1]
    failed = int(match.group("failed"))
    passed = int(match.group("passed"))
    status = match.group("status")
    return {
        "path": str(path),
        "ok": failed == 0 and status == "ok",
        "reason": None if failed == 0 and status == "ok" else "lib_suite_failed",
        "status": status,
        "passed": passed,
        "failed": failed,
        "ignored": int(match.group("ignored")),
    }


def check_search_report(path: Path) -> dict[str, Any]:
    data, error = read_json(path)
    if error:
        return {
            "path": str(path),
            "ok": False,
            "reason": error,
        }
    summary = data.get("summary") if isinstance(data, dict) and isinstance(data.get("summary"), dict) else {}
    failed = summary.get("failed")
    passed = summary.get("passed")
    skipped = summary.get("skipped")
    ok = failed == 0 and isinstance(passed, int) and passed > 0
    return {
        "path": str(path),
        "ok": ok,
        "reason": None if ok else "search_compat_report_not_green",
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
    }


def check_native_route_report(path: Path) -> dict[str, Any]:
    data, error = read_json(path)
    if error:
        return {
            "path": str(path),
            "ok": False,
            "reason": error,
        }
    summary = data.get("summary") if isinstance(data, dict) and isinstance(data.get("summary"), dict) else {}
    ok = bool(data.get("ok")) if isinstance(data, dict) else False
    return {
        "path": str(path),
        "ok": ok,
        "reason": None if ok else "native_route_coverage_not_green",
        "case_groups": summary.get("case_groups"),
        "passed": summary.get("passed"),
        "failed": summary.get("failed"),
        "missing_native_route_evidence": summary.get("missing_native_route_evidence"),
    }


def check_fixture_coverage_report(path: Path) -> dict[str, Any]:
    data, error = read_json(path)
    if error:
        return {
            "path": str(path),
            "ok": False,
            "reason": error,
        }
    summary = data.get("summary") if isinstance(data, dict) and isinstance(data.get("summary"), dict) else {}
    ok = bool(data.get("ok")) if isinstance(data, dict) else False
    return {
        "path": str(path),
        "ok": ok,
        "reason": None if ok else "native_route_fixture_coverage_not_green",
        "planned_groups": summary.get("planned_groups"),
        "covered_groups": summary.get("covered_groups"),
        "missing_groups": summary.get("missing_groups"),
        "unknown_groups": summary.get("unknown_groups"),
        "unprofiled_native_cases": summary.get("unprofiled_native_cases"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lib-log", type=Path, default=DEFAULT_LIB_LOG)
    parser.add_argument("--search-compat-report", type=Path, default=DEFAULT_SEARCH_REPORT)
    parser.add_argument("--native-route-fixture-report", type=Path, default=DEFAULT_FIXTURE_COVERAGE_REPORT)
    parser.add_argument("--native-route-report", type=Path, default=DEFAULT_NATIVE_ROUTE_REPORT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    checks = {
        "lib_suite": check_lib_log(args.lib_log),
        "search_compat": check_search_report(args.search_compat_report),
        "native_route_fixture_coverage": check_fixture_coverage_report(args.native_route_fixture_report),
        "native_route_coverage": check_native_route_report(args.native_route_report),
    }
    ok = all(check["ok"] for check in checks.values())
    report = {
        "schema_version": 1,
        "ok": ok,
        "checks": checks,
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n")
    else:
        print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
