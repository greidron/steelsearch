#!/usr/bin/env python3
"""Validate bulk promotion gate coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/bulk-promotion-gate.json",
    )
    return parser.parse_args()


def ensure_subset(name: str, actual: list[str], required: set[str]) -> None:
    missing = sorted(required - set(actual))
    if missing:
        raise SystemExit(f"{name} missing required entries: {missing}")


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))

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
        "semantic_parity.required_cases",
        semantic.get("required_cases") or [],
        {
            "global_bulk_optimistic_concurrency_success",
            "global_bulk_optimistic_concurrency_conflict",
            "global_bulk_auto_creates_missing_index",
            "global_bulk_create_into_data_stream_target",
            "global_bulk_partial_failure_item_shape",
            "global_bulk_refresh_pipeline_routing_shape",
            "get_bulk_routed_doc_after_wait_for_refresh",
            "global_bulk_external_version_create",
            "global_bulk_external_version_conflict",
            "index_scoped_bulk_default_target_update_upsert_shape",
            "bulk_routing_item_readback",
            "bulk_external_version_success_item",
            "bulk_external_version_conflict_item",
            "bulk_seq_term_success_item",
            "bulk_seq_term_conflict_item",
            "bulk_pipeline_metadata_unsupported_error",
            "bulk_version_without_external_policy_error",
            "bulk_item_ordering_partial_failure_matrix",
            "bulk_metadata_non_object_parse_error",
            "bulk_closed_index_item_failure_matrix",
            "bulk_refresh_false_readback_not_found",
            "bulk_refresh_true_readback",
            "bulk_refresh_wait_for_readback",
            "bulk_repeated_create_replay_conflict",
        },
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
