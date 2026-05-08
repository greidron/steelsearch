#!/usr/bin/env python3
"""Validate named writeable corpus coverage for transport compatibility fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/named-writeable-payload-corpus.json",
    )
    return parser.parse_args()


def require_hex(value: str, field: str, case_name: str) -> None:
    if len(value) % 2 != 0:
        raise SystemExit(f"{case_name}: {field} must contain an even-length hex string")
    try:
        bytes.fromhex(value)
    except ValueError as exc:
        raise SystemExit(f"{case_name}: invalid {field}: {exc}") from exc


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    cases = fixture.get("cases") or []
    if not cases:
        raise SystemExit("named writeable corpus is empty")

    supported = 0
    unsupported = 0
    seen_names: set[str] = set()

    for case in cases:
        case_name = case.get("case")
        if not case_name:
            raise SystemExit("case entry missing case name")
        if case_name in seen_names:
            raise SystemExit(f"duplicate case name: {case_name}")
        seen_names.add(case_name)

        family = case.get("registry_family")
        if family not in {"cluster_state_custom", "metadata_custom"}:
            raise SystemExit(f"{case_name}: unsupported registry_family {family!r}")

        named_writeable = case.get("named_writeable")
        if not named_writeable:
            raise SystemExit(f"{case_name}: missing named_writeable")

        compatibility = case.get("compatibility")
        expectation = case.get("decode_expectation")
        if compatibility == "supported":
            supported += 1
            if expectation != "decode_and_round_trip":
                raise SystemExit(
                    f"{case_name}: supported named writeable must use decode_and_round_trip"
                )
            round_trip_hex = case.get("round_trip_hex")
            if not round_trip_hex:
                raise SystemExit(f"{case_name}: supported case missing round_trip_hex")
            require_hex(round_trip_hex, "round_trip_hex", case_name)
        elif compatibility == "unsupported":
            unsupported += 1
            if expectation != "fail_closed":
                raise SystemExit(f"{case_name}: unsupported named writeable must fail_closed")
            if "round_trip_hex" in case:
                raise SystemExit(f"{case_name}: unsupported case must not include round_trip_hex")
        else:
            raise SystemExit(f"{case_name}: unsupported compatibility value {compatibility!r}")

        payload_hex = case.get("payload_hex")
        if not payload_hex:
            raise SystemExit(f"{case_name}: missing payload_hex")
        require_hex(payload_hex, "payload_hex", case_name)

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "case_count": len(cases),
                "supported_cases": supported,
                "unsupported_cases": unsupported,
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
