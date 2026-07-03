#!/usr/bin/env python3
"""Validate k-NN plugin promotion gate coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from promotion_report_evidence import resolve_required_report_paths, validate_report_evidence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/knn-plugin-promotion-gate.json",
    )
    parser.add_argument(
        "--report",
        action="append",
        default=None,
        help=(
            "Executed compatibility report to validate against required cases/evidence. "
            "Defaults to latest_standalone_gate.required_reports from the fixture."
        ),
    )
    return parser.parse_args()


def ensure_subset(name: str, actual: list[str], required: set[str]) -> None:
    missing = sorted(required - set(actual))
    if missing:
        raise SystemExit(f"{name} missing required entries: {missing}")


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))

    if fixture.get("source_area") != "k-NN plugin REST and model APIs":
        raise SystemExit("k-NN plugin promotion gate fixture has the wrong source_area")
    if fixture.get("profile") != "standalone":
        raise SystemExit("k-NN plugin promotion gate must target the standalone profile")

    expectation = fixture.get("matrix_expectation") or {}
    if expectation.get("open_search_api_compatibility") != "Implemented":
        raise SystemExit("k-NN plugin promotion expects OpenSearch API compatibility = Implemented")
    if expectation.get("production_readiness") != "Yes":
        raise SystemExit("k-NN plugin promotion expects Production readiness = Yes")

    sections = fixture.get("unified_report_sections") or {}
    for section_name in ("route_parity", "semantic_parity"):
        if section_name not in sections:
            raise SystemExit(f"missing unified report section: {section_name}")

    route = sections["route_parity"]
    semantic = sections["semantic_parity"]
    required_cases = {
        "knn_settings_readback",
        "knn_warmup_basic_shape",
        "knn_clear_cache_basic_shape",
        "knn_model_lifecycle_shape",
        "knn_warmup_post_method_not_allowed",
        "knn_warmup_clear_cache_telemetry_shape",
        "knn_faiss_method_engine_search",
        "knn_on_disk_mode_search",
    }
    required_evidence_classes = {
        "settings-readback",
        "warmup-cache",
        "clear-cache",
        "model-lifecycle",
        "method-boundary",
    }

    ensure_subset(
        "route_parity.required_suites",
        route.get("required_suites") or [],
        {"vector-ml"},
    )
    ensure_subset(
        "route_parity.report_paths",
        route.get("report_paths") or [],
        {"knn-plugin-compat-report.json"},
    )
    ensure_subset(
        "semantic_parity.report_paths",
        semantic.get("report_paths") or [],
        {"knn-plugin-compat-report.json"},
    )
    ensure_subset(
        "semantic_parity.required_cases",
        semantic.get("required_cases") or [],
        required_cases,
    )
    ensure_subset(
        "semantic_parity.required_evidence_classes",
        semantic.get("required_evidence_classes") or [],
        required_evidence_classes,
    )
    gate = fixture.get("latest_standalone_gate") or {}
    report_paths = args.report
    if report_paths is None:
        report_paths = gate.get("required_reports") or []
    if not report_paths:
        raise SystemExit("at least one k-NN compatibility report is required")
    resolved_reports = resolve_required_report_paths(report_paths)

    if report_paths:
        report_errors = validate_report_evidence(
            resolved_reports,
            required_cases,
            required_evidence_classes,
        )
        if report_errors:
            raise SystemExit("; ".join(report_errors))
    ensure_subset(
        "excluded_from_standalone_claim",
        fixture.get("excluded_from_standalone_claim") or [],
        {"secure-clustered-lifecycle"},
    )

    ensure_subset(
        "latest_standalone_gate.required_entrypoints",
        gate.get("required_entrypoints") or [],
        {"tools/run-phase-a-acceptance-harness.sh --mode local --scope vector-ml"},
    )
    ensure_subset(
        "latest_standalone_gate.required_reports",
        gate.get("required_reports") or [],
        {"knn-plugin-compat-report.json"},
    )

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "profile": fixture["profile"],
                "reports": [str(report) for report in resolved_reports],
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
