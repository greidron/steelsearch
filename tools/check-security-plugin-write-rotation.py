#!/usr/bin/env python3
"""Validate Security plugin write-mutation and cert-rotation bounded subset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/security-plugin-write-rotation-matrix.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    cases = fixture.get("cases") or []
    if not cases:
        raise SystemExit("security plugin write/rotation matrix is empty")

    counts = {"allowed": 0, "denied": 0}
    seen_routes = set()
    ssl_reload_covered = False

    for case in cases:
        case_name = case.get("case")
        route = case.get("route")
        method = case.get("method")
        credential_set = case.get("credential_set")
        expected_result = case.get("expected_result")
        expected_status = case.get("expected_status")
        mutation_result = case.get("mutation_result")
        if not case_name or not route or not method or not credential_set or not mutation_result:
            raise SystemExit("every plugin write case requires case/route/method/credential_set/mutation_result")
        seen_routes.add(route)
        if expected_result not in {"allowed", "denied"}:
            raise SystemExit(f"{case_name}: unsupported expected_result {expected_result!r}")
        if expected_result == "allowed":
            if expected_status != 200:
                raise SystemExit(f"{case_name}: allowed mutation must use 200")
            if mutation_result not in {"acknowledged", "reloaded"}:
                raise SystemExit(f"{case_name}: allowed mutation_result must be acknowledged or reloaded")
        else:
            if expected_status != 403:
                raise SystemExit(f"{case_name}: denied mutation must use 403")
            if mutation_result != "rejected":
                raise SystemExit(f"{case_name}: denied mutation_result must be rejected")
        if route.endswith("/reloadcerts"):
            ssl_reload_covered = True
        counts[expected_result] += 1

    if counts["allowed"] < 3 or counts["denied"] < 2:
        raise SystemExit("write/rotation matrix must include at least three allowed and two denied cases")
    if not ssl_reload_covered:
        raise SystemExit("write/rotation matrix must include cert reload coverage")

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "profile": fixture.get("profile"),
                "case_count": len(cases),
                "allowed_cases": counts["allowed"],
                "denied_cases": counts["denied"],
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
