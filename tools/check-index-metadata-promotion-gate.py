#!/usr/bin/env python3
"""Validate index-metadata promotion gate coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/index-metadata-promotion-gate.json",
    )
    return parser.parse_args()


def ensure_subset(name: str, actual: list[str], required: set[str]) -> None:
    missing = sorted(required - set(actual))
    if missing:
        raise SystemExit(f"{name} missing required entries: {missing}")


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))

    if fixture.get("source_area") != "Index create/get/delete and mappings/settings":
        raise SystemExit("index metadata promotion gate fixture has the wrong source_area")
    if fixture.get("profile") != "standalone":
        raise SystemExit("index metadata promotion gate must target the standalone profile")

    expectation = fixture.get("matrix_expectation") or {}
    if expectation.get("open_search_api_compatibility") != "Implemented":
        raise SystemExit("index metadata promotion expects OpenSearch API compatibility = Implemented")
    if expectation.get("production_readiness") != "Yes":
        raise SystemExit("index metadata promotion expects Production readiness = Yes")

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
        {"common-baseline"},
    )
    ensure_subset(
        "route_parity.report_paths",
        route.get("report_paths") or [],
        {
            "index-lifecycle-compat-report.json",
            "mapping-compat-report.json",
            "settings-compat-report.json",
            "alias-read-compat-report.json",
            "template-compat-report.json",
            "data-stream-rollover-compat-report.json",
            "search-compat-report.json",
        },
    )
    ensure_subset(
        "semantic_parity.required_cases",
        semantic.get("required_cases") or [],
        {
            "get_component_template_readback",
            "get_index_template_readback",
            "templated_index_application_readback",
            "get_data_stream_metadata_readback",
            "get_data_stream_stats_readback",
            "delete_data_stream_ack",
            "dynamic_mapping_readback",
            "mapping_conflict_reject",
            "settings_targeted_named_readback",
            "settings_targeted_flat_readback",
            "settings_global_named_readback",
            "wildcard_index_read_visible_only",
            "settings_hidden_wildcard_put_ack",
            "settings_hidden_target_readback",
            "wildcard_alias_readback",
            "get_created_alias_readback",
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
            "security_admin_restricted_index_get_success",
            "security_reader_restricted_index_get_403",
            "security_admin_restricted_settings_update_success",
            "security_writer_restricted_settings_update_403",
            "security_writer_restricted_delete_403",
            "security_admin_restricted_delete_success",
            "security_writer_restricted_create_403",
            "security_admin_restricted_create_success",
        },
    )

    gate = fixture.get("latest_standalone_gate") or {}
    ensure_subset(
        "latest_standalone_gate.required_entrypoints",
        gate.get("required_entrypoints") or [],
        {
            "tools/run-phase-a-acceptance-harness.sh --mode local --scope index-metadata",
            "tools/run-security-compat-harness.sh --profile single-node-secure",
        },
    )
    ensure_subset(
        "latest_standalone_gate.required_reports",
        gate.get("required_reports") or [],
        {
            "index-lifecycle-compat-report.json",
            "mapping-compat-report.json",
            "settings-compat-report.json",
            "alias-read-compat-report.json",
            "template-compat-report.json",
            "data-stream-rollover-compat-report.json",
            "search-compat-report.json",
            "security-authz-compat-report.json",
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
