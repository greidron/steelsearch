#!/usr/bin/env python3
"""Validate vector promotion gate coverage."""

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
        default="tools/fixtures/vector-promotion-gate.json",
    )
    parser.add_argument(
        "--vector-compat-fixture",
        default="tools/fixtures/vector-search-compat.json",
        help="Vector compatibility fixture whose cases must be promoted.",
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
    vector_compat = json.loads(Path(args.vector_compat_fixture).read_text(encoding="utf-8"))

    if fixture.get("source_area") != "k-NN vector indexing and query search":
        raise SystemExit("vector promotion gate fixture has the wrong source_area")
    if fixture.get("profile") != "standalone":
        raise SystemExit("vector promotion gate must target the standalone profile")

    expectation = fixture.get("matrix_expectation") or {}
    if expectation.get("open_search_api_compatibility") != "Implemented":
        raise SystemExit("vector promotion expects OpenSearch API compatibility = Implemented")
    if expectation.get("production_readiness") != "Yes":
        raise SystemExit("vector promotion expects Production readiness = Yes")

    sections = fixture.get("unified_report_sections") or {}
    for section_name in ("route_parity", "semantic_parity"):
        if section_name not in sections:
            raise SystemExit(f"missing unified report section: {section_name}")

    route = sections["route_parity"]
    semantic = sections["semantic_parity"]
    required_cases = {case["name"] for case in vector_compat.get("cases", [])}
    required_evidence_classes = {
        "lucene-score-space",
        "byte-vector-subset",
        "binary-vector-subset",
        "nested-filtered-knn",
        "exact-ranking",
        "hybrid-score-merge",
    }

    ensure_subset(
        "route_parity.required_suites",
        route.get("required_suites") or [],
        {"vector-ml"},
    )
    ensure_subset(
        "route_parity.report_paths",
        route.get("report_paths") or [],
        {
            "vector-search-compat-report.json",
            "vector-search-native-surface-report.json",
        },
    )
    ensure_subset(
        "semantic_parity.report_paths",
        semantic.get("report_paths") or [],
        {"vector-search-native-surface-report.json"},
    )
    ensure_subset(
        "semantic_parity.required_cases",
        semantic.get("required_cases") or [],
        required_cases,
    )
    stale_required_cases = sorted(set(semantic.get("required_cases") or []) - required_cases)
    if stale_required_cases:
        raise SystemExit(
            "semantic_parity.required_cases contains non-vector-compat entries: "
            f"{stale_required_cases}"
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
        raise SystemExit("at least one vector compatibility report is required")
    resolved_reports = resolve_required_report_paths(report_paths)

    if report_paths:
        report_errors = validate_report_evidence(
            resolved_reports,
            required_cases,
            required_evidence_classes,
        )
        if report_errors:
            raise SystemExit("; ".join(report_errors))

    reject = fixture.get("reject_ledger") or {}
    if reject.get("fixture") != "vector-reject-ledger.json":
        raise SystemExit("vector promotion gate must point at vector-reject-ledger.json")
    ensure_subset(
        "reject_ledger.required_categories",
        reject.get("required_categories") or [],
        {"space", "data_type"},
    )

    ensure_subset(
        "latest_standalone_gate.required_entrypoints",
        gate.get("required_entrypoints") or [],
        {"tools/run-phase-a-acceptance-harness.sh --mode local --scope vector-ml"},
    )
    ensure_subset(
        "latest_standalone_gate.required_reports",
        gate.get("required_reports") or [],
        {"vector-search-native-surface-report.json"},
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
