#!/usr/bin/env python3
"""Validate tenant, role, and index-permission security matrix fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/security-tenant-role-index-matrix.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    cases = fixture.get("cases") or []
    if not cases:
        raise SystemExit("security tenant/role/index matrix is empty")

    counts = {"allowed": 0, "denied": 0}
    required_credentials = {"reader-basic", "writer-basic", "admin-basic"}
    seen_credentials = set()
    cross_tenant_denies = 0
    restricted_denies = 0

    for case in cases:
        case_name = case.get("case")
        credential_set = case.get("credential_set")
        operation = case.get("operation")
        target = case.get("target")
        expected_result = case.get("expected_result")
        expected_status = case.get("expected_status")
        reason = case.get("reason")
        if not case_name or not credential_set or not operation or not target or expected_status is None or not reason:
            raise SystemExit("every security matrix case requires case/credential_set/operation/target/status/reason")
        if credential_set not in required_credentials:
            raise SystemExit(f"{case_name}: unsupported credential_set {credential_set!r}")
        seen_credentials.add(credential_set)
        if expected_result not in {"allowed", "denied"}:
            raise SystemExit(f"{case_name}: unsupported expected_result {expected_result!r}")
        counts[expected_result] += 1
        if expected_result == "allowed" and expected_status not in {200, 201}:
            raise SystemExit(f"{case_name}: allowed case must use 200 or 201")
        if expected_result == "denied" and expected_status != 403:
            raise SystemExit(f"{case_name}: denied case must use 403")
        if "cross_tenant" in case_name:
            cross_tenant_denies += 1
        if ".opensearch-restricted" in target or "restricted-authz-alias" == target:
            if expected_result == "denied":
                restricted_denies += 1

    if seen_credentials != required_credentials:
        raise SystemExit("tenant/role matrix must cover reader-basic, writer-basic, and admin-basic")
    if cross_tenant_denies == 0:
        raise SystemExit("tenant/role matrix must include at least one cross-tenant deny case")
    if restricted_denies < 2:
        raise SystemExit("tenant/role matrix must include at least two restricted-target deny cases")

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
