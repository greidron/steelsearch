#!/usr/bin/env python3
"""Validate document-write promotion gate coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_COMPAT_FIXTURES = [
    "tools/fixtures/single-doc-crud-compat.json",
    "tools/fixtures/refresh-compat.json",
    "tools/fixtures/routing-compat.json",
    "tools/fixtures/bulk-compat.json",
    "tools/fixtures/document-write-semantic-compat.json",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/document-write-promotion-gate.json",
    )
    parser.add_argument(
        "--compat-fixture",
        action="append",
        default=[],
        help="Document-write compatibility fixture whose cases must be promoted.",
    )
    return parser.parse_args()


def ensure_subset(name: str, actual: list[str], required: set[str]) -> None:
    missing = sorted(required - set(actual))
    if missing:
        raise SystemExit(f"{name} missing required entries: {missing}")


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    compat_fixture_paths = args.compat_fixture or DEFAULT_COMPAT_FIXTURES
    required_cases = set()
    for compat_fixture_path in compat_fixture_paths:
        compat_fixture = json.loads(Path(compat_fixture_path).read_text(encoding="utf-8"))
        required_cases.update(
            case["name"]
            for case in compat_fixture.get("cases", [])
            if isinstance(case, dict) and case.get("name")
        )

    if fixture.get("source_area") != "Document write/read and refresh":
        raise SystemExit("document-write promotion gate fixture has the wrong source_area")
    if fixture.get("profile") != "standalone":
        raise SystemExit("document-write promotion gate must target the standalone profile")

    expectation = fixture.get("matrix_expectation") or {}
    if expectation.get("open_search_api_compatibility") != "Implemented":
        raise SystemExit("document-write promotion expects OpenSearch API compatibility = Implemented")
    if expectation.get("production_readiness") != "Yes":
        raise SystemExit("document-write promotion expects Production readiness = Yes")

    sections = fixture.get("unified_report_sections") or {}
    for section_name in ("route_parity", "semantic_parity", "durability_parity"):
        if section_name not in sections:
            raise SystemExit(f"missing unified report section: {section_name}")

    route = sections["route_parity"]
    semantic = sections["semantic_parity"]
    durability = sections["durability_parity"]

    ensure_subset(
        "route_parity.required_suites",
        route.get("required_suites") or [],
        {"common-baseline"},
    )
    ensure_subset(
        "route_parity.report_paths",
        route.get("report_paths") or [],
        {
            "single-doc-crud-compat-report.json",
            "refresh-compat-report.json",
            "routing-compat-report.json",
            "bulk-compat-report.json",
        },
    )
    ensure_subset(
        "semantic_parity.report_paths",
        semantic.get("report_paths") or [],
        {"document-write-semantic-compat-report.json"},
    )
    ensure_subset(
        "semantic_parity.required_cases",
        semantic.get("required_cases") or [],
        required_cases,
    )
    stale_required_cases = sorted(set(semantic.get("required_cases") or []) - required_cases)
    if stale_required_cases:
        raise SystemExit(
            "semantic_parity.required_cases contains non-document-write compat entries: "
            f"{stale_required_cases}"
        )
    ensure_subset(
        "durability_parity.required_suites",
        durability.get("required_suites") or [],
        {"write-path-multi-node"},
    )
    ensure_subset(
        "durability_parity.report_paths",
        durability.get("report_paths") or [],
        {"multi-node-write-path-report.json"},
    )

    gate = fixture.get("latest_standalone_gate") or {}
    ensure_subset(
        "latest_standalone_gate.required_entrypoints",
        gate.get("required_entrypoints") or [],
        {
            "tools/run-phase-a-acceptance-harness.sh --mode local --scope document-write-path",
            "python3 tools/multi_node_write_path_integration.py ...",
        },
    )
    ensure_subset(
        "latest_standalone_gate.required_reports",
        gate.get("required_reports") or [],
        {
            "single-doc-crud-compat-report.json",
            "refresh-compat-report.json",
            "routing-compat-report.json",
            "bulk-compat-report.json",
            "document-write-semantic-compat-report.json",
            "multi-node-write-path-report.json",
        },
    )

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "profile": fixture["profile"],
                "source_area": fixture["source_area"],
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
