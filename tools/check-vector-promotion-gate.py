#!/usr/bin/env python3
"""Validate vector promotion gate coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/vector-promotion-gate.json",
    )
    return parser.parse_args()


def ensure_subset(name: str, actual: list[str], required: set[str]) -> None:
    missing = sorted(required - set(actual))
    if missing:
        raise SystemExit(f"{name} missing required entries: {missing}")


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))

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
        {
            "knn_search",
            "knn_cosinesimil_search",
            "knn_innerproduct_search",
            "knn_query_happy_path",
            "knn_query_filter_happy_path",
            "knn_query_ignore_unmapped_happy_path",
            "knn_query_radial_max_distance_happy_path",
            "knn_query_method_parameters_happy_path",
            "hybrid_query_happy_path",
            "hybrid_should_query_happy_path",
            "hybrid_minimum_should_match_happy_path",
        },
    )
    ensure_subset(
        "semantic_parity.required_evidence_classes",
        semantic.get("required_evidence_classes") or [],
        {
            "lucene-score-space",
            "byte-vector-subset",
            "binary-vector-subset",
            "nested-filtered-knn",
            "exact-ranking",
            "hybrid-score-merge",
        },
    )

    reject = fixture.get("reject_ledger") or {}
    if reject.get("fixture") != "vector-reject-ledger.json":
        raise SystemExit("vector promotion gate must point at vector-reject-ledger.json")
    ensure_subset(
        "reject_ledger.required_categories",
        reject.get("required_categories") or [],
        {"engine", "mode", "space", "data_type"},
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
