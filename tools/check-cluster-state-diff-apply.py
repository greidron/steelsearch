#!/usr/bin/env python3
"""Validate cluster-state full-vs-diff apply transcript fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/cluster-state-diff-apply-transcript.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    cases = fixture.get("cases") or []
    if not cases:
        raise SystemExit("cluster-state diff apply transcript is empty")

    allowed_decode = {"decoded", "rejected"}
    allowed_apply = {"applied", "preserved_prior_cache"}
    summary = {"decoded_and_applied": 0, "rejected_and_preserved": 0}

    for case in cases:
        case_name = case.get("case")
        if not case_name:
            raise SystemExit("case entry missing case name")
        if case.get("publication_mode") != "diff":
            raise SystemExit(f"{case_name}: publication_mode must be diff")
        if not case.get("custom_name"):
            raise SystemExit(f"{case_name}: custom_name is required")
        if case.get("decode_result") not in allowed_decode:
            raise SystemExit(f"{case_name}: unsupported decode_result")
        if case.get("apply_result") not in allowed_apply:
            raise SystemExit(f"{case_name}: unsupported apply_result")

        transcript = case.get("transcript") or []
        if transcript[:2] != ["full-state decoded", "prior cache snapshot recorded"]:
            raise SystemExit(
                f"{case_name}: transcript must start with full-state decode and prior cache snapshot"
            )
        if case["decode_result"] == "decoded":
            if case["apply_result"] != "applied":
                raise SystemExit(f"{case_name}: decoded diff must be applied")
            if case["prior_cache_state"] == case["post_apply_cache_state"]:
                raise SystemExit(f"{case_name}: applied diff must mutate cache state")
            summary["decoded_and_applied"] += 1
        else:
            if case["apply_result"] != "preserved_prior_cache":
                raise SystemExit(f"{case_name}: rejected diff must preserve prior cache")
            if case["prior_cache_state"] != case["post_apply_cache_state"]:
                raise SystemExit(f"{case_name}: rejected diff changed cache state")
            summary["rejected_and_preserved"] += 1

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "case_count": len(cases),
                "decoded_and_applied": summary["decoded_and_applied"],
                "rejected_and_preserved": summary["rejected_and_preserved"],
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
