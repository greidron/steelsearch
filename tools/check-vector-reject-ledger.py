#!/usr/bin/env python3
"""Validate vector reject-ledger coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/vector-reject-ledger.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    entries = fixture.get("entries") or []
    if not entries:
        raise SystemExit("vector reject ledger is empty")

    required = {"engine", "mode", "space", "data_type"}
    seen = set()
    for entry in entries:
        case = entry.get("case")
        category = entry.get("category")
        expected = entry.get("expected_result")
        if not case or not category or not expected:
            raise SystemExit("each vector reject entry requires case/category/expected_result")
        if expected != "fail-closed":
            raise SystemExit(f"{case}: expected_result must be fail-closed")
        seen.add(category)

    if seen != required:
        raise SystemExit(f"vector reject ledger missing categories: {sorted(required - seen)}")

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
