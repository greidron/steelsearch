#!/usr/bin/env python3
import json
import sys
from pathlib import Path


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

SEMANTIC_CASE_CHECKS = {
    "template_metadata": {
        "component_template_metadata_summary",
        "index_template_metadata_summary",
    },
    "index_metadata": {"concrete_index_metadata_summary"},
    "alias_metadata": {"alias_metadata_summary"},
    "data_stream_metadata": {"data_stream_metadata_summary"},
    "scroll_export_sequence": {"scroll_export_sequence"},
    "pit_export_sequence": {"pit_export_sequence"},
    "vector_payload_summary_doc": {"vector_payload_summary_doc"},
}

SEMANTIC_EVIDENCE_CHECKS = {
    "translation-breadth": {
        "component_template_metadata_summary",
        "index_template_metadata_summary",
        "concrete_index_metadata_summary",
        "alias_metadata_summary",
        "data_stream_metadata_summary",
    },
    "scroll-export": {"scroll_export_sequence"},
    "pit-export": {"pit_export_sequence"},
    "vector-payload-equivalence": {"vector_payload_summary_doc"},
}


def fail(message: str) -> None:
    raise SystemExit(message)


def resolve_report(name: str) -> Path:
    direct = Path(name)
    if direct.exists():
        return direct
    matches = sorted(
        Path("target").glob(f"**/{direct.name}"),
        key=lambda candidate: candidate.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        fail(f"required report is missing: {name}")
    return matches[0]


def validate_cutover_integration_report(name: str) -> None:
    report_path = resolve_report(name)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    checks = {
        check.get("name"): check
        for check in report.get("checks", [])
        if isinstance(check, dict) and check.get("name")
    }
    if not checks:
        fail(f"{report_path}: missing cutover checks")

    for case_name, check_names in SEMANTIC_CASE_CHECKS.items():
        missing = sorted(check_names - set(checks))
        if missing:
            fail(f"{report_path}: {case_name} missing checks {missing}")
        failed = sorted(
            check_name
            for check_name in check_names
            if checks[check_name].get("match") is not True
            or checks[check_name].get("skipped") is True
        )
        if failed:
            fail(f"{report_path}: {case_name} failed checks {failed}")

    for evidence_class, check_names in SEMANTIC_EVIDENCE_CHECKS.items():
        if not all(checks[check_name].get("match") is True for check_name in check_names):
            fail(f"{report_path}: missing evidence class {evidence_class}")

    resume = report.get("resume") or {}
    if not resume.get("checkpoint"):
        fail(f"{report_path}: missing resumability checkpoint evidence")
    if not resume.get("completed_operations_after_run"):
        fail(f"{report_path}: missing completed operation checkpoint evidence")


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
    validate_cutover_integration_report("migration-cutover-integration-report.json")

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
