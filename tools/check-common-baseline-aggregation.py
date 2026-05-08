#!/usr/bin/env python3
"""Validate that common-baseline aggregation covers all required profile families."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/common-baseline-aggregation-matrix.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    families = fixture.get("families") or {}
    required_families = {
        "search",
        "write",
        "snapshot",
        "security",
        "runtime",
        "mixed-cluster",
    }
    if set(families.keys()) != required_families:
        raise SystemExit(
            f"common-baseline aggregation missing families: {sorted(required_families - set(families.keys()))}"
        )

    for family_name, family in families.items():
        profiles = family.get("profiles") or []
        required_reports = family.get("required_reports") or []
        if not profiles:
            raise SystemExit(f"{family_name}: profiles must not be empty")
        if not required_reports:
            raise SystemExit(f"{family_name}: required_reports must not be empty")

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "family_count": len(families),
                "families": sorted(families.keys()),
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
