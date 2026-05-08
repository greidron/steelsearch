#!/usr/bin/env python3
"""Validate unified comparison report schema fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/unified-comparison-report-schema.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    required_top_level_fields = fixture.get("required_top_level_fields") or []
    parity_sections = fixture.get("parity_sections") or {}
    status_values = fixture.get("status_values") or []
    if not required_top_level_fields or not parity_sections or not status_values:
        raise SystemExit("unified comparison schema fixture is incomplete")

    required_sections = {
        "route_parity",
        "semantic_parity",
        "durability_parity",
        "security_parity",
        "distributed_parity",
    }
    if set(parity_sections.keys()) != required_sections:
        raise SystemExit(
            f"unified comparison schema missing parity sections: {sorted(required_sections - set(parity_sections.keys()))}"
        )
    if set(required_sections).difference(required_top_level_fields):
        raise SystemExit("every parity section must also be listed in required_top_level_fields")

    for section_name, fields in parity_sections.items():
        if fields != ["required_suites", "report_paths", "status"]:
            raise SystemExit(f"{section_name}: unexpected field layout {fields!r}")

    if set(status_values) != {"ok", "missing", "blocked"}:
        raise SystemExit(f"unexpected status_values: {status_values!r}")

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "required_top_level_field_count": len(required_top_level_fields),
                "parity_section_count": len(parity_sections),
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
