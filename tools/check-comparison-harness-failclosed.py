#!/usr/bin/env python3
"""Validate fail-closed smoke coverage for comparison harness drift/report issues."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/comparison-harness-failclosed-smoke.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    cases = fixture.get("cases") or []
    if not cases:
        raise SystemExit("comparison harness fail-closed smoke fixture is empty")

    expected_classes = {
        "fixture_drift",
        "missing_report_field",
        "stale_generated_artifact",
    }
    seen_classes = set()
    for case in cases:
        case_name = case.get("case")
        failure_class = case.get("failure_class")
        expected_result = case.get("expected_result")
        markers = case.get("required_markers") or []
        if not case_name or not failure_class or not expected_result:
            raise SystemExit("every fail-closed case requires case/failure_class/expected_result")
        if expected_result != "blocked":
            raise SystemExit(f"{case_name}: expected_result must be blocked")
        if len(markers) < 2:
            raise SystemExit(f"{case_name}: required_markers must include at least two markers")
        seen_classes.add(failure_class)

    if seen_classes != expected_classes:
        raise SystemExit(
            f"comparison harness fail-closed smoke missing classes: {sorted(expected_classes - seen_classes)}"
        )

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "case_count": len(cases),
                "failure_classes": sorted(seen_classes),
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
