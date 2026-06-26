#!/usr/bin/env python3
"""Validate cluster-admin promotion gate coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_COMPAT_FIXTURES = [
    "tools/fixtures/cluster-health-compat.json",
    "tools/fixtures/allocation-explain-compat.json",
    "tools/fixtures/cluster-settings-compat.json",
    "tools/fixtures/cluster-state-compat.json",
    "tools/fixtures/tasks-compat.json",
    "tools/fixtures/stats-compat.json",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/cluster-admin-promotion-gate.json",
    )
    parser.add_argument(
        "--compat-fixture",
        action="append",
        default=[],
        help="Cluster-admin compatibility fixture whose cases must be promoted.",
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

    if fixture.get("source_area") != "Cluster health, state, allocation, and node stats":
        raise SystemExit("cluster-admin promotion gate fixture has the wrong source_area")
    if fixture.get("profile") != "standalone":
        raise SystemExit("cluster-admin promotion gate must target the standalone profile")

    expectation = fixture.get("matrix_expectation") or {}
    if expectation.get("open_search_api_compatibility") != "Implemented":
        raise SystemExit("cluster-admin promotion expects OpenSearch API compatibility = Implemented")
    if expectation.get("production_readiness") != "Yes":
        raise SystemExit("cluster-admin promotion expects Production readiness = Yes")

    sections = fixture.get("unified_report_sections") or {}
    for section_name in ("route_parity", "semantic_parity", "distributed_parity"):
        if section_name not in sections:
            raise SystemExit(f"missing unified report section: {section_name}")

    route = sections["route_parity"]
    semantic = sections["semantic_parity"]
    distributed = sections["distributed_parity"]

    ensure_subset(
        "route_parity.required_suites",
        route.get("required_suites") or [],
        {"common-baseline"},
    )
    ensure_subset(
        "route_parity.report_paths",
        route.get("report_paths") or [],
        {
            "cluster-health-compat-report.json",
            "allocation-explain-compat-report.json",
            "cluster-settings-compat-report.json",
            "cluster-state-compat-report.json",
            "tasks-compat-report.json",
            "stats-compat-report.json",
            "search-compat-report.json",
        },
    )
    ensure_subset(
        "semantic_parity.required_cases",
        semantic.get("required_cases") or [],
        required_cases,
    )
    stale_required_cases = sorted(set(semantic.get("required_cases") or []) - required_cases)
    if stale_required_cases:
        raise SystemExit(
            "semantic_parity.required_cases contains non-cluster-admin compat entries: "
            f"{stale_required_cases}"
        )
    ensure_subset(
        "distributed_parity.required_suites",
        distributed.get("required_suites") or [],
        {"transport-admin"},
    )
    ensure_subset(
        "distributed_parity.report_paths",
        distributed.get("report_paths") or [],
        {"multi-node-transport-admin-report.json"},
    )

    standalone_fields = distributed.get("standalone_only_fields") or []
    distributed_fields = distributed.get("distributed_required_fields") or []
    if not standalone_fields:
        raise SystemExit("distributed_parity.standalone_only_fields must not be empty")
    if not distributed_fields:
        raise SystemExit("distributed_parity.distributed_required_fields must not be empty")
    overlap = sorted(set(standalone_fields) & set(distributed_fields))
    if overlap:
        raise SystemExit(f"field boundary overlap detected: {overlap}")

    gate = fixture.get("latest_standalone_gate") or {}
    ensure_subset(
        "latest_standalone_gate.required_entrypoints",
        gate.get("required_entrypoints") or [],
        {
            "tools/run-phase-a-acceptance-harness.sh --mode local",
            "tools/run-phase-a-acceptance-harness.sh --mode local --scope transport-admin",
        },
    )
    ensure_subset(
        "latest_standalone_gate.required_reports",
        gate.get("required_reports") or [],
        {
            "cluster-health-compat-report.json",
            "allocation-explain-compat-report.json",
            "cluster-settings-compat-report.json",
            "cluster-state-compat-report.json",
            "tasks-compat-report.json",
            "stats-compat-report.json",
            "search-compat-report.json",
            "multi-node-transport-admin-report.json",
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
