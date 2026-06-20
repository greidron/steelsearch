#!/usr/bin/env python3
"""Validate unsupported search option fail-closed coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/search-unsupported-option-deny-ledger.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    entries = fixture.get("entries") or []
    if not entries:
        raise SystemExit("search unsupported-option deny ledger is empty")

    required = {
        "runtime_mappings_request_body_fail_closed",
    }
    seen = set()
    for entry in entries:
        case = entry.get("case")
        surface = entry.get("surface")
        expected = entry.get("expected_result")
        evidence = entry.get("evidence")
        if not case or not surface or not expected or not evidence:
            raise SystemExit("each deny-ledger entry requires case/surface/expected_result/evidence")
        if expected != "fail-closed":
            raise SystemExit(f"{case}: expected_result must be fail-closed")
        seen.add(case)

    if seen != required:
        raise SystemExit(f"search deny ledger missing required cases: {sorted(required - seen)}")

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "entry_count": len(entries),
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
