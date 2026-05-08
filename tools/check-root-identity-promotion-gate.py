#!/usr/bin/env python3
"""Validate root-identity promotion gate coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/root-identity-promotion-gate.json",
    )
    return parser.parse_args()


def ensure_subset(name: str, actual: list[str], required: set[str]) -> None:
    missing = sorted(required - set(actual))
    if missing:
        raise SystemExit(f"{name} missing required entries: {missing}")


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))

    if fixture.get("source_area") != "Root and basic node identity":
        raise SystemExit("root identity promotion gate fixture has the wrong source_area")
    if fixture.get("profile") != "standalone":
        raise SystemExit("root identity promotion gate must target the standalone profile")

    expectation = fixture.get("matrix_expectation") or {}
    if expectation.get("open_search_api_compatibility") != "Implemented":
        raise SystemExit("root identity promotion expects OpenSearch API compatibility = Implemented")
    if expectation.get("production_readiness") != "Yes":
        raise SystemExit("root identity promotion expects Production readiness = Yes")

    sections = fixture.get("unified_report_sections") or {}
    for section_name in ("route_parity", "semantic_parity", "security_parity"):
        if section_name not in sections:
            raise SystemExit(f"missing unified report section: {section_name}")

    route = sections["route_parity"]
    semantic = sections["semantic_parity"]
    security = sections["security_parity"]

    ensure_subset(
        "route_parity.required_suites",
        route.get("required_suites") or [],
        {"root-cluster-node"},
    )
    ensure_subset(
        "semantic_parity.required_suites",
        semantic.get("required_suites") or [],
        {"root-cluster-node"},
    )
    ensure_subset(
        "route_parity.report_paths",
        route.get("report_paths") or [],
        {"root-cluster-node-compat-report.json"},
    )
    ensure_subset(
        "semantic_parity.report_paths",
        semantic.get("report_paths") or [],
        {"root-cluster-node-compat-report.json"},
    )
    ensure_subset(
        "route_parity.required_cases",
        route.get("required_cases") or [],
        {"root_info"},
    )
    ensure_subset(
        "semantic_parity.required_cases",
        semantic.get("required_cases") or [],
        {"root_info"},
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
            "security_missing_root_info_401",
            "security_bad_password_root_info_401",
            "security_reader_root_info_success",
        },
    )

    gate = fixture.get("latest_standalone_gate") or {}
    ensure_subset(
        "latest_standalone_gate.required_reports",
        gate.get("required_reports") or [],
        {"root-cluster-node-compat-report.json", "security-authz-compat-report.json"},
    )
    ensure_subset(
        "latest_standalone_gate.required_entrypoints",
        gate.get("required_entrypoints") or [],
        {
            "tools/run-phase-a-acceptance-harness.sh --mode local --scope root-cluster-node",
            "tools/run-security-compat-harness.sh --profile single-node-secure",
        },
    )
    ensure_subset(
        "latest_standalone_gate.required_status_body_contracts",
        gate.get("required_status_body_contracts") or [],
        {
            "GET / root_info",
            "HEAD / empty-body",
            "GET / 401 missing-auth",
            "GET / 401 bad-password",
            "GET / 200 reader-auth",
        },
    )

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "source_area": fixture["source_area"],
                "profile": fixture["profile"],
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
