#!/usr/bin/env python3
"""Validate promotion-ledger coverage for official compatibility promotion work."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/compatibility-promotion-ledger.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    entries = fixture.get("entries") or []
    if not entries:
        raise SystemExit("compatibility promotion ledger fixture is empty")

    buckets = {
        "promoted": 0,
        "promotion-ready": 0,
        "promotion-blocked": 0,
        "optional-track": 0,
    }
    required_optional = {
        "Java OpenSearch data-node compatibility",
        "Java plugin ABI compatibility",
    }
    seen_optional = set()

    for entry in entries:
        source_area = entry.get("source_area")
        target_profile = entry.get("target_profile")
        bucket = entry.get("promotion_bucket")
        if not source_area or not target_profile or not bucket:
            raise SystemExit("every promotion ledger entry requires source_area/target_profile/promotion_bucket")
        if bucket not in buckets:
            raise SystemExit(f"{source_area}: unsupported promotion bucket {bucket!r}")
        buckets[bucket] += 1
        if bucket == "optional-track":
            seen_optional.add(source_area)

    if seen_optional != required_optional:
        raise SystemExit(
            f"promotion ledger missing optional-track rows: {sorted(required_optional - seen_optional)}"
        )
    if buckets["promoted"] == 0:
        raise SystemExit("promotion ledger must contain at least one promoted row")
    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "entry_count": len(entries),
                "buckets": buckets,
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
