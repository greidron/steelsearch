#!/usr/bin/env python3
"""Validate required multi-node transport/admin report coverage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_PIT_CASES = {
    "node_a_open_pit",
    "node_b_search_node_a_pit",
    "node_b_close_node_a_pit",
    "node_b_search_node_a_pit_after_close",
    "node_a_list_pits_after_node_b_close",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", help="multi-node-transport-admin-report.json")
    parser.add_argument(
        "--require-remote-pit",
        action="store_true",
        help="require the remote REST PIT search/close transport cases to pass",
    )
    return parser.parse_args()


def load_report(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"report not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON report {path}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"report must be a JSON object: {path}")
    return data


def case_statuses(report: dict[str, Any]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for case in report.get("cases", []):
        if not isinstance(case, dict):
            continue
        name = case.get("name")
        status = case.get("status")
        if isinstance(name, str) and isinstance(status, str):
            statuses[name] = status
    return statuses


def main() -> int:
    args = parse_args()
    report = load_report(Path(args.report))
    statuses = case_statuses(report)
    errors: list[str] = []

    summary = report.get("summary", {})
    if not isinstance(summary, dict) or summary.get("failed") != 0:
        errors.append("report summary must have failed=0")

    for case in report.get("cases", []):
        if isinstance(case, dict) and case.get("status") != "passed":
            errors.append(f"case {case.get('name')!r} did not pass")

    for check in report.get("post_checks", []):
        if isinstance(check, dict) and check.get("status") != "passed":
            errors.append(f"post_check {check.get('name')!r} did not pass")

    missing_remote_pit_cases: list[str] = []
    failed_remote_pit_cases: list[str] = []
    if args.require_remote_pit:
        missing_remote_pit_cases = sorted(REQUIRED_PIT_CASES - statuses.keys())
        failed_remote_pit_cases = sorted(
            case for case in REQUIRED_PIT_CASES if statuses.get(case) != "passed"
        )
        if missing_remote_pit_cases:
            errors.append(f"missing remote PIT cases: {missing_remote_pit_cases}")
        if failed_remote_pit_cases:
            errors.append(f"remote PIT cases not passed: {failed_remote_pit_cases}")

    payload = {
        "summary": {
            "passed": not errors,
            "failed_count": len(errors),
            "remote_pit_required": bool(args.require_remote_pit),
            "remote_pit_case_count": len(REQUIRED_PIT_CASES & statuses.keys()),
        },
        "errors": errors,
        "missing_remote_pit_cases": missing_remote_pit_cases,
        "failed_remote_pit_cases": failed_remote_pit_cases,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
