#!/usr/bin/env python3
"""Validate snapshot promotion gate coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/snapshot-promotion-gate.json",
    )
    return parser.parse_args()


def ensure_subset(name: str, actual: list[str], required: set[str]) -> None:
    missing = sorted(required - set(actual))
    if missing:
        raise SystemExit(f"{name} missing required entries: {missing}")


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))

    if fixture.get("source_area") != "Snapshot and restore":
        raise SystemExit("snapshot promotion gate fixture has the wrong source_area")
    if fixture.get("profile") != "standalone":
        raise SystemExit("snapshot promotion gate must target the standalone profile")

    expectation = fixture.get("matrix_expectation") or {}
    if expectation.get("open_search_api_compatibility") != "Implemented":
        raise SystemExit("snapshot promotion expects OpenSearch API compatibility = Implemented")
    if expectation.get("production_readiness") != "Yes":
        raise SystemExit("snapshot promotion expects Production readiness = Yes")

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
        {"snapshot-migration"},
    )
    ensure_subset(
        "route_parity.report_paths",
        route.get("report_paths") or [],
        {"snapshot-lifecycle-compat-report.json"},
    )
    ensure_subset(
        "semantic_parity.required_cases",
        semantic.get("required_cases") or [],
        {
            "register_snapshot_repository",
            "get_snapshot_repository",
            "verify_snapshot_repository",
            "create_snapshot_happy_path",
            "get_snapshot_happy_path",
            "get_snapshot_status_happy_path",
            "restore_snapshot_happy_path",
            "delete_snapshot_happy_path",
            "cleanup_snapshot_repository_happy_path",
            "restore_snapshot_stale_metadata_failure",
            "restore_snapshot_corrupt_metadata_failure",
            "restore_snapshot_incompatible_metadata_failure",
            "restore_missing_snapshot_failure",
            "cleanup_missing_snapshot_repository_failure",
        },
    )
    ensure_subset(
        "semantic_parity.required_evidence_classes",
        semantic.get("required_evidence_classes") or [],
        {
            "incremental-snapshot",
            "remote-readonly-repository",
            "searchable-snapshot-mount",
            "restore-option-breadth",
            "repository-type-validation",
            "restore-precondition-safety",
            "cutover-linkage",
        },
    )
    ensure_subset(
        "durability_parity.report_paths",
        durability.get("report_paths") or [],
        {"migration-acceptance/report.json"},
    )

    gate = fixture.get("latest_standalone_gate") or {}
    ensure_subset(
        "latest_standalone_gate.required_entrypoints",
        gate.get("required_entrypoints") or [],
        {"tools/run-phase-a-acceptance-harness.sh --mode local --scope snapshot-migration"},
    )
    ensure_subset(
        "latest_standalone_gate.required_reports",
        gate.get("required_reports") or [],
        {"snapshot-lifecycle-compat-report.json", "migration-acceptance/report.json"},
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
