#!/usr/bin/env python3
import json
import sys


EXPECTED_REPORTS = {
    "security-authz-compat-report.json",
    "secure-multinode-tls-report.json",
    "security-tenant-role-index-report.json",
    "security-audit-correlation-report.json",
    "security-plugin-api-report.json",
    "security-plugin-write-rotation-report.json",
    "secure-multinode-gap-harness/report.json",
}

EXPECTED_CASES = {
    "security_missing_root_info_401",
    "security_reader_root_info_success",
    "security_reader_restricted_index_get_403",
    "security_admin_restricted_index_get_success",
    "security_writer_bulk_partial_authz_denial",
}

EXPECTED_EVIDENCE = {
    "tls-handshake-matrix",
    "tenant-role-index-isolation",
    "restricted-index-policy",
    "audit-correlation",
    "plugin-api-secret-redaction",
    "plugin-write-cert-rotation",
    "secure-multinode-join",
    "secure-cert-rotation",
    "restricted-index-mutation-deny",
}

EXPECTED_FINAL_EVIDENCE = {
    "secure-redaction-smoke",
    "secure-durability-restart",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check-security-row-reclassification-gate.py <fixture.json>")

    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("source_area") != "Security and access control":
        fail("unexpected source_area")
    if data.get("profile") != "secure-standalone":
        fail("unexpected profile")

    matrix = data.get("matrix_expectation", {})
    if matrix.get("open_search_api_compatibility") != "Implemented":
        fail("open_search_api_compatibility must be Implemented")
    if matrix.get("semantic_parity") != "Implemented":
        fail("semantic_parity must be Implemented")
    if matrix.get("production_readiness") != "Implemented":
        fail("production_readiness must be Implemented")
    if matrix.get("replacement_ready") != "Yes":
        fail("replacement_ready must be Yes")

    section = data.get("unified_report_sections", {}).get("security_parity")
    if not section:
        fail("security_parity section required")
    if section.get("suite") != "security-multinode":
        fail("security_parity suite mismatch")
    if set(section.get("required_reports", [])) != EXPECTED_REPORTS:
        fail("required_reports mismatch")
    if set(section.get("required_cases", [])) != EXPECTED_CASES:
        fail("required_cases mismatch")
    if set(section.get("required_evidence_classes", [])) != EXPECTED_EVIDENCE:
        fail("required_evidence_classes mismatch")

    final_gate = data.get("final_claim_gate", {})
    if final_gate.get("report") != "secure-standalone-claim-report.json":
        fail("final_claim_gate report mismatch")
    if final_gate.get("required_status") != "ok":
        fail("final_claim_gate required_status must be ok")
    if set(final_gate.get("required_evidence_classes", [])) != EXPECTED_FINAL_EVIDENCE:
        fail("final_claim_gate required_evidence_classes mismatch")
    if "redaction smoke" not in final_gate.get("reason", ""):
        fail("final gate reason must mention redaction smoke")

    print(json.dumps({
        "source_area": data["source_area"],
        "profile": data["profile"],
        "production_readiness": matrix["production_readiness"],
        "replacement_ready": matrix["replacement_ready"],
        "status": "ok"
    }))


if __name__ == "__main__":
    main()
