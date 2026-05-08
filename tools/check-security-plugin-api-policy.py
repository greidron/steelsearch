#!/usr/bin/env python3
"""Validate representative Security plugin API parity and secret-redaction policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/security-plugin-api-secret-policy.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    cases = fixture.get("cases") or []
    if not cases:
        raise SystemExit("security plugin API policy fixture is empty")

    counts = {"allowed": 0, "denied": 0}
    required_routes = {
        "/_plugins/_security/api/account",
        "/_plugins/_security/api/internalusers",
        "/_plugins/_security/api/roles",
        "/_plugins/_security/api/rolesmapping",
        "/_plugins/_security/api/ssl/certs",
    }
    seen_routes = set()

    for case in cases:
        case_name = case.get("case")
        route = case.get("route")
        method = case.get("method")
        credential_set = case.get("credential_set")
        expected_result = case.get("expected_result")
        expected_status = case.get("expected_status")
        redaction_markers = case.get("secret_redaction_markers") or []
        if not case_name or not route or not method or not credential_set:
            raise SystemExit("every plugin API case requires case/route/method/credential_set")
        seen_routes.add(route)
        if expected_result not in {"allowed", "denied"}:
            raise SystemExit(f"{case_name}: unsupported expected_result {expected_result!r}")
        if expected_result == "allowed" and expected_status != 200:
            raise SystemExit(f"{case_name}: allowed plugin API case must use 200")
        if expected_result == "denied" and expected_status != 403:
            raise SystemExit(f"{case_name}: denied plugin API case must use 403")
        if len(redaction_markers) < 2:
            raise SystemExit(f"{case_name}: secret_redaction_markers must contain at least two markers")
        counts[expected_result] += 1

    if seen_routes != required_routes:
        raise SystemExit(
            f"plugin API policy missing required routes: {sorted(required_routes - seen_routes)}"
        )

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
