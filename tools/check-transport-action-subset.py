#!/usr/bin/env python3
"""Validate declared allow/reject transport action subset coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/transport-action-subset-ledger.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    cases = fixture.get("cases") or []
    if not cases:
        raise SystemExit("transport action subset ledger is empty")

    allowed = 0
    rejected = 0
    server_side_families: set[str] = set()

    for case in cases:
        case_name = case.get("case")
        if not case_name:
            raise SystemExit("case entry missing case name")
        action = case.get("action")
        transport_class = case.get("transport_class")
        route_family = case.get("route_family")
        if not action or not transport_class or not route_family:
            raise SystemExit(f"{case_name}: action, transport_class, route_family are required")

        bucket = case.get("bucket")
        disposition = case.get("disposition")
        family = case.get("family")
        if family not in {"read", "search", "write"}:
            raise SystemExit(f"{case_name}: unsupported family {family!r}")

        if bucket == "server-side":
            if disposition != "allowed":
                raise SystemExit(f"{case_name}: server-side bucket must be allowed")
            server_side_families.add(family)
            allowed += 1
        elif bucket == "planned":
            if disposition != "rejected":
                raise SystemExit(f"{case_name}: planned bucket must be rejected")
            rejected += 1
        else:
            raise SystemExit(f"{case_name}: unsupported bucket {bucket!r}")

        reason = case.get("reason")
        if not reason:
            raise SystemExit(f"{case_name}: reason is required")

    if "search" not in server_side_families or "write" not in server_side_families:
        raise SystemExit("transport action subset must include at least one server-side search and write action")

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "case_count": len(cases),
                "allowed_cases": allowed,
                "rejected_cases": rejected,
                "server_side_families": sorted(server_side_families),
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
