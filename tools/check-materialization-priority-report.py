#!/usr/bin/env python3
"""Validate materialization-priority report invariants."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--require-passed", action="store_true")
    parser.add_argument("--require-zero-ranked", action="store_true")
    args = parser.parse_args()

    payload = json.loads(args.report.read_text(encoding="utf-8"))
    result = validate_report(
        payload,
        require_passed=args.require_passed,
        require_zero_ranked=args.require_zero_ranked,
    )
    print(json.dumps({"report": str(args.report), **result}, indent=2, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


def validate_report(
    payload: dict[str, Any],
    *,
    require_passed: bool = False,
    require_zero_ranked: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    priorities = payload.get("priorities") if isinstance(payload.get("priorities"), list) else []
    ranked_operation_count = summary.get("ranked_operation_count")
    observed_operation_count = summary.get("observed_operation_count")
    successful_operation_count = summary.get("successful_operation_count")
    counter_observed_operation_count = summary.get("counter_observed_operation_count")

    if require_passed and summary.get("passed") is not True:
        errors.append("summary.passed is not true")
    if not isinstance(ranked_operation_count, int):
        errors.append("summary.ranked_operation_count is missing or not an integer")
    elif ranked_operation_count != len(priorities):
        errors.append(
            "summary.ranked_operation_count does not match priorities length "
            f"({ranked_operation_count} != {len(priorities)})"
        )
    if require_zero_ranked and ranked_operation_count != 0:
        errors.append(f"ranked_operation_count is {ranked_operation_count}, expected 0")
    if require_zero_ranked:
        if not isinstance(observed_operation_count, int) or observed_operation_count <= 0:
            errors.append("summary.observed_operation_count must be a positive integer")
        if not isinstance(successful_operation_count, int) or successful_operation_count <= 0:
            errors.append("summary.successful_operation_count must be a positive integer")
        if not isinstance(counter_observed_operation_count, int) or counter_observed_operation_count <= 0:
            errors.append("summary.counter_observed_operation_count must be a positive integer")

    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary": {
            "passed": summary.get("passed"),
            "allow_empty": summary.get("allow_empty"),
            "observed_operation_count": observed_operation_count,
            "successful_operation_count": successful_operation_count,
            "counter_observed_operation_count": counter_observed_operation_count,
            "ranked_operation_count": ranked_operation_count,
            "priority_rows": len(priorities),
            "top_operation": summary.get("top_operation"),
            "top_family": summary.get("top_family"),
        },
    }


if __name__ == "__main__":
    sys.exit(main())
