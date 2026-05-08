#!/usr/bin/env python3
import json
import sys


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

    if data.get("required_inputs") != EXPECTED_INPUTS:
        fail("required_inputs mismatch")
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
