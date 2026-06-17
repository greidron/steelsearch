#!/usr/bin/env python3
"""Validate secure multi-node TLS handshake matrix fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/secure-multinode-tls-handshake-matrix.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    cases = fixture.get("cases") or []
    if not cases:
        raise SystemExit("secure multi-node TLS handshake matrix is empty")

    counts = {"connected": 0, "rejected": 0}
    required_buckets = {
        "success",
        "client-cert-success",
        "wrong-ca-failure",
        "expired-cert-failure",
    }
    seen_buckets = set()

    for case in cases:
        case_name = case.get("case")
        bucket = case.get("bucket")
        result = case.get("expected_result")
        mode = case.get("transport_mode")
        client_auth = case.get("client_auth")
        markers = case.get("expected_markers") or []
        if not case_name or not bucket or not result or not mode or not client_auth:
            raise SystemExit("every TLS matrix case requires case/bucket/result/mode/client_auth")
        if bucket not in required_buckets:
            raise SystemExit(f"{case_name}: unsupported bucket {bucket!r}")
        seen_buckets.add(bucket)
        if result not in {"connected", "rejected"}:
            raise SystemExit(f"{case_name}: unsupported expected_result {result!r}")
        if len(markers) < 2:
            raise SystemExit(f"{case_name}: expected_markers must include at least two markers")
        counts[result] += 1

    if seen_buckets != required_buckets:
        raise SystemExit(
            f"TLS handshake matrix missing required buckets: {sorted(required_buckets - seen_buckets)}"
        )

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "profile": fixture.get("profile"),
                "case_count": len(cases),
                "connected_cases": counts["connected"],
                "rejected_cases": counts["rejected"],
                "summary": {
                    "passed": True,
                    "case_count": len(cases),
                    "connected_cases": counts["connected"],
                    "rejected_cases": counts["rejected"],
                },
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
