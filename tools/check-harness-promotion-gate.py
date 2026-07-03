#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED_INPUTS = {
    "suite_manifest": "comparison-harness-required-suites.json",
    "unified_schema": "unified-comparison-report-schema.json",
    "baseline_aggregation": "common-baseline-aggregation-matrix.json",
    "fail_closed_smoke": "comparison-harness-failclosed-smoke.json",
}

EXPECTED_CLASSES = {
    "fixture_drift",
    "missing_report_field",
    "stale_generated_artifact",
}

EXPECTED_ENTRYPOINTS = {
    "tools/run-phase-a-acceptance-harness.sh --mode local",
    "tools/run-secure-multinode-gap-harness.sh --profile <name> ...",
    "tools/run-phase-b-gap-harness.sh --profile <name> ...",
    "tools/run-phase-c-gap-harness.sh --profile <name> ...",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def fixture_path(name: str) -> Path:
    path = Path(__file__).resolve().parents[1] / "tools" / "fixtures" / name
    if not path.exists():
        fail(f"required harness input is missing: {name}")
    return path


def validate_required_inputs(inputs: dict[str, str]) -> None:
    if inputs != EXPECTED_INPUTS:
        fail("required_inputs mismatch")

    suite_manifest = json.loads(fixture_path(inputs["suite_manifest"]).read_text(encoding="utf-8"))
    profiles = suite_manifest.get("profiles") or {}
    if not profiles:
        fail("suite manifest profiles must not be empty")
    for profile_name, profile in profiles.items():
        if not profile.get("entrypoint"):
            fail(f"{profile_name}: missing suite manifest entrypoint")
        if not profile.get("required_reports"):
            fail(f"{profile_name}: missing suite manifest required_reports")

    schema = json.loads(fixture_path(inputs["unified_schema"]).read_text(encoding="utf-8"))
    required_sections = {
        "route_parity",
        "semantic_parity",
        "durability_parity",
        "security_parity",
        "distributed_parity",
    }
    if set((schema.get("parity_sections") or {}).keys()) != required_sections:
        fail("unified schema parity_sections mismatch")
    if set(schema.get("status_values") or []) != {"ok", "missing", "blocked"}:
        fail("unified schema status_values mismatch")

    baseline = json.loads(fixture_path(inputs["baseline_aggregation"]).read_text(encoding="utf-8"))
    if not baseline.get("families"):
        fail("baseline aggregation families must not be empty")

    fail_closed = json.loads(fixture_path(inputs["fail_closed_smoke"]).read_text(encoding="utf-8"))
    observed_classes = {
        case.get("failure_class")
        for case in fail_closed.get("cases", [])
        if isinstance(case, dict) and case.get("failure_class")
    }
    if observed_classes != EXPECTED_CLASSES:
        fail("fail-closed smoke failure classes mismatch")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check-harness-promotion-gate.py <fixture.json>")

    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("source_area") != "OpenSearch comparison harness":
        fail("unexpected source_area")
    if data.get("profile") != "all-profiles":
        fail("unexpected profile")

    matrix = data.get("matrix_expectation", {})
    if matrix.get("open_search_api_compatibility") != "Implemented":
        fail("open_search_api_compatibility must be Implemented")
    if matrix.get("semantic_parity") != "N/A":
        fail("semantic_parity must be N/A")
    if matrix.get("production_readiness") != "Yes":
        fail("production_readiness must be Yes")

    validate_required_inputs(data.get("required_inputs") or {})
    if set(data.get("required_fail_closed_classes", [])) != EXPECTED_CLASSES:
        fail("required_fail_closed_classes mismatch")
    if set(data.get("latest_harness_entrypoints", [])) != EXPECTED_ENTRYPOINTS:
        fail("latest_harness_entrypoints mismatch")

    print(json.dumps({
        "source_area": data["source_area"],
        "profile": data["profile"],
        "status": "ok"
    }))


if __name__ == "__main__":
    main()
