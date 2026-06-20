#!/usr/bin/env python3
"""Validate ML promotion gate coverage."""

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
        default="tools/fixtures/ml-promotion-gate.json",
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

    if fixture.get("source_area") != "ML Commons, neural search, and model serving":
        raise SystemExit("ML promotion gate fixture has the wrong source_area")
    if fixture.get("profile") != "standalone":
        raise SystemExit("ML promotion gate must target the standalone profile")

    expectation = fixture.get("matrix_expectation") or {}
    if expectation.get("open_search_api_compatibility") != "Implemented":
        raise SystemExit("ML promotion expects OpenSearch API compatibility = Implemented")
    if expectation.get("production_readiness") != "Yes":
        raise SystemExit("ML promotion expects Production readiness = Yes")

    sections = fixture.get("unified_report_sections") or {}
    for section_name in ("route_parity", "semantic_parity", "security_parity"):
        if section_name not in sections:
            raise SystemExit(f"missing unified report section: {section_name}")

    route = sections["route_parity"]
    semantic = sections["semantic_parity"]
    security = sections["security_parity"]
    semantic_required_cases = {
        "ml_model_lifecycle_shape",
        "neural_query_search",
        "rerank_pipeline_search",
        "sparse_encoder_search",
    }
    semantic_required_evidence_classes = {
        "task-lifecycle",
        "connector-authz",
        "deploy-persistence",
        "neural-query-rewrite",
        "rerank-pipeline",
        "sparse-encoder",
        "runtime-isolation",
        "deployment-isolation",
    }
    security_required_cases = {
        "security_bad_password_ml_register_401",
        "security_writer_ml_connector_create_403",
        "security_admin_ml_connector_create_success",
        "security_writer_ml_predict_403",
    }

    ensure_subset(
        "route_parity.required_suites",
        route.get("required_suites") or [],
        {"vector-ml"},
    )
    ensure_subset(
        "route_parity.report_paths",
        route.get("report_paths") or [],
        {"ml-model-surface-compat-report.json"},
    )
    ensure_subset(
        "semantic_parity.required_cases",
        semantic.get("required_cases") or [],
        semantic_required_cases,
    )
    ensure_subset(
        "semantic_parity.required_evidence_classes",
        semantic.get("required_evidence_classes") or [],
        semantic_required_evidence_classes,
    )
    ensure_subset(
        "security_parity.report_paths",
        security.get("report_paths") or [],
        {"security-authz-compat-report.json"},
    )
    ensure_subset(
        "security_parity.required_cases",
        security.get("required_cases") or [],
        security_required_cases,
    )
    if args.report:
        report_errors = validate_report_evidence(
            [Path(report) for report in args.report],
            semantic_required_cases | security_required_cases,
            semantic_required_evidence_classes,
        )
        if report_errors:
            raise SystemExit("; ".join(report_errors))

    gate = fixture.get("latest_standalone_gate") or {}
    ensure_subset(
        "latest_standalone_gate.required_entrypoints",
        gate.get("required_entrypoints") or [],
        {
            "tools/run-phase-a-acceptance-harness.sh --mode local --scope vector-ml",
            "tools/run-security-compat-harness.sh --profile single-node-secure",
        },
    )
    ensure_subset(
        "latest_standalone_gate.required_reports",
        gate.get("required_reports") or [],
        {"ml-model-surface-compat-report.json", "security-authz-compat-report.json"},
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
