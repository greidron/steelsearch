#!/usr/bin/env python3
"""Validate security audit/correlation fixture coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/security-audit-correlation-matrix.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    cases = fixture.get("cases") or []
    if not cases:
        raise SystemExit("security audit/correlation matrix is empty")

    counts = {"access_granted": 0, "access_denied": 0}
    seen_correlation_ids = set()

    for case in cases:
        case_name = case.get("case")
        event_type = case.get("event_type")
        correlation_id = case.get("correlation_id")
        required_fields = case.get("required_fields") or []
        redaction_markers = case.get("redaction_markers") or []
        expected_result = case.get("expected_result")
        if not case_name or not event_type or not correlation_id or not expected_result:
            raise SystemExit("every audit case requires case/event_type/correlation_id/expected_result")
        if correlation_id in seen_correlation_ids:
            raise SystemExit(f"duplicate correlation_id: {correlation_id}")
        seen_correlation_ids.add(correlation_id)
        if event_type not in {"access_granted", "access_denied"}:
            raise SystemExit(f"{case_name}: unsupported event_type {event_type!r}")
        if expected_result != "recorded":
            raise SystemExit(f"{case_name}: expected_result must be recorded")
        counts[event_type] += 1
        if len(required_fields) < 5:
            raise SystemExit(f"{case_name}: required_fields must include at least five audit fields")
        if "correlation_id" not in required_fields:
            raise SystemExit(f"{case_name}: required_fields must include correlation_id")
        if len(redaction_markers) < 2:
            raise SystemExit(f"{case_name}: redaction_markers must include auth and password redaction")

    if counts["access_granted"] == 0 or counts["access_denied"] < 2:
        raise SystemExit("audit matrix must include one granted event and at least two denied events")

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "profile": fixture.get("profile"),
                "case_count": len(cases),
                "access_granted": counts["access_granted"],
                "access_denied": counts["access_denied"],
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
