#!/usr/bin/env python3
"""Validate document-write promotion gate coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/document-write-promotion-gate.json",
    )
    return parser.parse_args()


def ensure_subset(name: str, actual: list[str], required: set[str]) -> None:
    missing = sorted(required - set(actual))
    if missing:
        raise SystemExit(f"{name} missing required entries: {missing}")


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))

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
        },
    )
    ensure_subset(
        "semantic_parity.required_cases",
        semantic.get("required_cases") or [],
        {
            "put_single_doc_explicit_id",
            "get_single_doc_filtered_source",
            "put_single_doc_external_version_success",
            "put_single_doc_external_version_conflict",
            "update_single_doc_optimistic_concurrency_success",
            "update_single_doc_optimistic_concurrency_conflict",
            "single_doc_routing_get_not_found",
            "single_doc_source_includes_readback",
            "single_doc_get_realtime_false_not_found",
            "single_doc_stored_fields_unsupported_error",
            "single_doc_put_lifecycle_get_not_found",
            "single_doc_create_refresh_false",
            "single_doc_get_realtime_false_after_refresh_false",
            "single_doc_create_refresh_wait_for",
            "single_doc_get_realtime_false_after_refresh_wait_for",
            "single_doc_create_refresh_true",
            "single_doc_get_realtime_false_after_refresh_true",
        },
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
