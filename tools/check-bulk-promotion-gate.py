#!/usr/bin/env python3
"""Validate bulk promotion gate coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_BULK_SEMANTIC_FIXTURE = "tools/fixtures/document-write-semantic-compat.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/bulk-promotion-gate.json",
    )
    parser.add_argument(
        "--bulk-compat-fixture",
        default="tools/fixtures/bulk-compat.json",
        help="Bulk compatibility fixture whose cases must be promoted.",
    )
    parser.add_argument(
        "--bulk-semantic-fixture",
        default=DEFAULT_BULK_SEMANTIC_FIXTURE,
        help="Document-write semantic fixture whose bulk_* cases must be promoted.",
    )
    return parser.parse_args()


def ensure_subset(name: str, actual: list[str], required: set[str]) -> None:
    missing = sorted(required - set(actual))
    if missing:
        raise SystemExit(f"{name} missing required entries: {missing}")


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    bulk_compat = json.loads(Path(args.bulk_compat_fixture).read_text(encoding="utf-8"))
    bulk_semantic = json.loads(Path(args.bulk_semantic_fixture).read_text(encoding="utf-8"))
    required_cases = {
        case["name"]
        for case in bulk_compat.get("cases", [])
        if isinstance(case, dict) and case.get("name")
    }
    required_cases.update(
        case["name"]
        for case in bulk_semantic.get("cases", [])
        if isinstance(case, dict)
        and isinstance(case.get("name"), str)
        and case["name"].startswith("bulk_")
    )

    if fixture.get("source_area") != "REST `_bulk`":
        raise SystemExit("bulk promotion gate fixture has the wrong source_area")
    if fixture.get("profile") != "standalone":
        raise SystemExit("bulk promotion gate must target the standalone profile")

    expectation = fixture.get("matrix_expectation") or {}
    if expectation.get("open_search_api_compatibility") != "Implemented":
        raise SystemExit("bulk promotion expects OpenSearch API compatibility = Implemented")
    if expectation.get("production_readiness") != "Yes":
        raise SystemExit("bulk promotion expects Production readiness = Yes")

    sections = fixture.get("unified_report_sections") or {}
    for section_name in ("route_parity", "semantic_parity", "security_parity", "durability_parity"):
        if section_name not in sections:
            raise SystemExit(f"missing unified report section: {section_name}")

    route = sections["route_parity"]
    semantic = sections["semantic_parity"]
    security = sections["security_parity"]
    durability = sections["durability_parity"]

    ensure_subset(
        "route_parity.required_suites",
        route.get("required_suites") or [],
        {"common-baseline"},
    )
    ensure_subset(
        "route_parity.report_paths",
        route.get("report_paths") or [],
        {"bulk-compat-report.json"},
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
            "semantic_parity.required_cases contains non-bulk promotion entries: "
            f"{stale_required_cases}"
        )
    ensure_subset(
        "security_parity.report_paths",
        security.get("report_paths") or [],
        {"security-authz-compat-report.json"},
    )
    ensure_subset(
        "security_parity.required_cases",
        security.get("required_cases") or [],
        {
            "security_writer_bulk_success",
            "security_admin_bulk_success",
            "security_reader_bulk_403",
            "security_writer_bulk_partial_authz_denial",
        },
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
            "tools/run-security-compat-harness.sh --profile single-node-secure",
            "python3 tools/multi_node_write_path_integration.py ...",
        },
    )
    ensure_subset(
        "latest_standalone_gate.required_reports",
        gate.get("required_reports") or [],
        {
            "bulk-compat-report.json",
            "document-write-semantic-compat-report.json",
            "security-authz-compat-report.json",
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
