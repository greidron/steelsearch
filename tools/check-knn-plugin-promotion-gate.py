#!/usr/bin/env python3
"""Validate k-NN plugin promotion gate coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from promotion_report_evidence import validate_report_evidence


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
        default=[],
        help="Executed compatibility report to validate against required cases/evidence.",
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
        "knn_warmup_budget_failure",
        "knn_warmup_clear_cache_telemetry_shape",
    }
    required_evidence_classes = {
        "settings-readback",
        "warmup-cache",
        "clear-cache",
        "model-lifecycle",
        "budget-breaker",
    }

    ensure_subset(
        "route_parity.required_suites",
        route.get("required_suites") or [],
        {"vector-ml"},
    )
    ensure_subset(
        "route_parity.report_paths",
        route.get("report_paths") or [],
        {"vector-search-compat-report.json"},
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
    if args.report:
        report_errors = validate_report_evidence(
            [Path(report) for report in args.report],
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

    gate = fixture.get("latest_standalone_gate") or {}
    ensure_subset(
        "latest_standalone_gate.required_entrypoints",
        gate.get("required_entrypoints") or [],
        {"tools/run-phase-a-acceptance-harness.sh --mode local --scope vector-ml"},
    )
    ensure_subset(
        "latest_standalone_gate.required_reports",
        gate.get("required_reports") or [],
        {"vector-search-compat-report.json"},
    )

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "profile": fixture["profile"],
                "reports": args.report,
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
