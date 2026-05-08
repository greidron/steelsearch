#!/usr/bin/env python3
"""Validate in-scope workstream definition for Java data-node compatibility."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/java-data-node-scope-matrix.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    workstreams = fixture.get("workstreams") or []
    if not workstreams:
        raise SystemExit("java data-node scope matrix is empty")

    required_areas = {
        "mixed_java_membership",
        "lucene_segment_binary_sharing",
        "jvm_recovery_participation",
    }
    seen_areas = set()

    for item in workstreams:
        area = item.get("area")
        scope_status = item.get("scope_status")
        harness = item.get("required_harness")
        evidence = item.get("required_evidence") or []
        blocked_reason = item.get("blocked_reason")
        if not area or not scope_status or not harness or not blocked_reason:
            raise SystemExit("every workstream requires area/scope_status/required_harness/blocked_reason")
        if scope_status != "in-scope":
            raise SystemExit(f"{area}: scope_status must be in-scope")
        if len(evidence) < 2:
            raise SystemExit(f"{area}: required_evidence must list at least two artifacts")
        seen_areas.add(area)

    if seen_areas != required_areas:
        raise SystemExit(f"scope matrix missing areas: {sorted(required_areas - seen_areas)}")

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "workstream_count": len(workstreams),
                "areas": sorted(seen_areas),
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
