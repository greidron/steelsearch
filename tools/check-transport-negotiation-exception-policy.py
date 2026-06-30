#!/usr/bin/env python3
"""Validate transport negotiation, exception mapping, and action classification policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/transport-negotiation-exception-policy.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    cases = fixture.get("cases") or []
    if not cases:
        raise SystemExit("transport negotiation/exception policy fixture is empty")

    counts = {
        "frame_negotiation": 0,
        "exception_mapping": 0,
        "action_classification": 0,
        "allowed": 0,
        "rejected": 0,
    }
    server_side = set()

    for case in cases:
        case_name = case.get("case")
        category = case.get("category")
        disposition = case.get("disposition")
        reason = case.get("reason")
        kind = case.get("kind")
        if not case_name or not category or not disposition or not reason or not kind:
            raise SystemExit("every policy case requires case/category/disposition/reason/kind")
        if category not in {"frame_negotiation", "exception_mapping", "action_classification"}:
            raise SystemExit(f"{case_name}: unsupported category {category!r}")
        counts[category] += 1

        if disposition not in {"allowed", "rejected"}:
            raise SystemExit(f"{case_name}: unsupported disposition {disposition!r}")
        counts[disposition] += 1

        if category in {"frame_negotiation", "exception_mapping"}:
            mapped_error = case.get("mapped_error")
            if disposition != "rejected":
                raise SystemExit(f"{case_name}: negotiation/exception cases must reject")
            if not mapped_error:
                raise SystemExit(f"{case_name}: missing mapped_error")

        if category == "action_classification":
            bucket = case.get("bucket")
            if bucket not in {"server-side", "planned", "unsupported"}:
                raise SystemExit(f"{case_name}: unsupported bucket {bucket!r}")
            if bucket == "server-side":
                if disposition != "allowed":
                    raise SystemExit(f"{case_name}: server-side action must be allowed")
                server_side.add(kind)
            else:
                if disposition != "rejected":
                    raise SystemExit(f"{case_name}: non-server-side action must be rejected")

    required_server_side = {
        "ClusterStateAction.INSTANCE",
        "SearchAction.INSTANCE",
        "BulkAction.INSTANCE",
        "MultiSearchAction.INSTANCE",
        "SearchScrollAction.INSTANCE",
        "ExplainAction.INSTANCE",
        "StreamSearchAction.INSTANCE",
    }
    if not required_server_side.issubset(server_side):
        raise SystemExit("missing required server-side transport actions in policy fixture")

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "case_count": len(cases),
                "counts": counts,
                "server_side_actions": sorted(server_side),
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
