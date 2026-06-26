#!/usr/bin/env python3
import json
import sys


EXPECTED_CASES = {
    "template_metadata",
    "index_metadata",
    "alias_metadata",
    "data_stream_metadata",
    "scroll_export_sequence",
    "pit_export_sequence",
    "vector_payload_summary_doc",
}

EXPECTED_SEMANTIC_EVIDENCE = {
    "translation-breadth",
    "scroll-export",
    "pit-export",
    "resumability-checkpoint",
    "vector-payload-equivalence",
}

EXPECTED_DURABILITY_EVIDENCE = {
    "approval-gate",
    "rollback-only-rehearsal",
    "rollback-divergence-two-dataset",
    "unsupported-feature-preflight",
}

EXPECTED_FINAL_FIELDS = {
    "approval_gate",
    "preflight",
    "rollback",
    "vector_validation",
    "divergence_check",
    "final_decision",
}

EXPECTED_REPORTS = {
    "migration-cutover-integration-report.json",
    "migration-acceptance/report.json",
    "migration-cutover-go-no-go-report.json",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check-migration-promotion-gate.py <fixture.json>")

    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("source_area") != "Migration and replacement tooling":
        fail("unexpected source_area")
    if data.get("profile") != "standalone":
        fail("unexpected profile")

    matrix = data.get("matrix_expectation", {})
    if matrix.get("open_search_api_compatibility") != "Implemented":
        fail("open_search_api_compatibility must be Implemented")
    if matrix.get("semantic_parity") != "N/A":
        fail("semantic_parity must be N/A")
    if matrix.get("production_readiness") != "Yes":
        fail("production_readiness must be Yes")

    sections = data.get("unified_report_sections", {})
    semantic = sections.get("semantic_parity")
    durability = sections.get("durability_parity")
    if not semantic or not durability:
        fail("semantic_parity and durability_parity are required")

    if set(semantic.get("required_cases", [])) != EXPECTED_CASES:
        fail("semantic required_cases mismatch")
    if set(semantic.get("required_evidence_classes", [])) != EXPECTED_SEMANTIC_EVIDENCE:
        fail("semantic evidence classes mismatch")
    if semantic.get("suite") != "snapshot-migration":
        fail("semantic suite mismatch")
    if set(semantic.get("required_reports", [])) != {"migration-cutover-integration-report.json"}:
        fail("semantic reports mismatch")

    if durability.get("suite") != "snapshot-migration":
        fail("durability suite mismatch")
    if set(durability.get("required_reports", [])) != {"migration-acceptance/report.json"}:
        fail("durability reports mismatch")
    if set(durability.get("required_evidence_classes", [])) != EXPECTED_DURABILITY_EVIDENCE:
        fail("durability evidence classes mismatch")

    final_report = data.get("final_cutover_go_no_go_report", {})
    if final_report.get("path") != "migration-cutover-go-no-go-report.json":
        fail("final cutover report path mismatch")
    if set(final_report.get("required_fields", [])) != EXPECTED_FINAL_FIELDS:
        fail("final cutover report required_fields mismatch")

    latest = data.get("latest_standalone_gate", {})
    if not latest.get("required_entrypoint", "").startswith("tools/run-migration-acceptance-harness.sh"):
        fail("latest gate entrypoint mismatch")
    if set(latest.get("required_reports", [])) != EXPECTED_REPORTS:
        fail("latest gate required_reports mismatch")

    print(json.dumps({
        "source_area": data["source_area"],
        "profile": data["profile"],
        "status": "ok"
    }))


if __name__ == "__main__":
    main()
