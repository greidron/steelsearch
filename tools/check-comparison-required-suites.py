#!/usr/bin/env python3
"""Validate profile-to-required-suite coverage for comparison harnesses."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/comparison-harness-required-suites.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    profiles = fixture.get("profiles") or {}
    if not profiles:
        raise SystemExit("comparison required suites fixture is empty")

    required_profiles = {
        "common-baseline",
        "vector-ml",
        "snapshot-migration",
        "transport-admin",
        "write-path-multi-node",
        "search-execution",
        "security-multinode",
        "external-interop",
        "same-cluster-peer",
    }
    if set(profiles.keys()) != required_profiles:
        missing = sorted(required_profiles - set(profiles.keys()))
        raise SystemExit(f"comparison required suites missing profiles: {missing}")

    for profile_name, profile in profiles.items():
        route_families = profile.get("route_families") or []
        required_reports = profile.get("required_reports") or []
        entrypoint = profile.get("entrypoint")
        if not entrypoint:
            raise SystemExit(f"{profile_name}: missing entrypoint")
        if len(route_families) < 3:
            raise SystemExit(f"{profile_name}: route_families must include at least three families")
        if not required_reports:
            raise SystemExit(f"{profile_name}: required_reports must not be empty")

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "profile_count": len(profiles),
                "profiles": sorted(profiles.keys()),
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
