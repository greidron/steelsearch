#!/usr/bin/env python3
import json
import sys


EXPECTED_ROUTE_EVIDENCE = {
    "handshake-version-gate",
    "stale-cache-failover",
    "allowlisted-forwarding",
    "mixed-mode-failure-harness",
}

EXPECTED_SEMANTIC_EVIDENCE = {
    "named-writeable-roundtrip",
    "cluster-state-diff-apply",
}

EXPECTED_ALLOWED_ACTIONS = {
    "ClusterStateAction.INSTANCE",
    "SearchAction.INSTANCE",
    "BulkAction.INSTANCE",
}

EXPECTED_REJECTED_ACTIONS = {
    "MultiSearchAction.INSTANCE",
    "StreamSearchAction.INSTANCE",
}

EXPECTED_LEDGERS = {
    "transport-action-subset-ledger.json",
    "transport-negotiation-exception-policy.json",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check-external-interop-promotion-gate.py <fixture.json>")

    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("source_area") != "Native transport frame and OpenSearch probe compatibility":
        fail("unexpected source_area")
    if data.get("profile") != "external-interop":
        fail("unexpected profile")

    matrix = data.get("matrix_expectation", {})
    if matrix.get("open_search_api_compatibility") != "Implemented":
        fail("open_search_api_compatibility must be Implemented")
    if matrix.get("semantic_parity") != "N/A":
        fail("semantic_parity must be N/A")
    if matrix.get("production_readiness") != "Yes":
        fail("production_readiness must be Yes")

    sections = data.get("unified_report_sections", {})
    route = sections.get("route_parity")
    semantic = sections.get("semantic_parity")
    if not route or not semantic:
        fail("route_parity and semantic_parity required")
    if route.get("suite") != "external-interop":
        fail("route_parity suite mismatch")
    if semantic.get("suite") != "external-interop":
        fail("semantic_parity suite mismatch")
    if set(route.get("required_evidence_classes", [])) != EXPECTED_ROUTE_EVIDENCE:
        fail("route evidence mismatch")
    if set(semantic.get("required_evidence_classes", [])) != EXPECTED_SEMANTIC_EVIDENCE:
        fail("semantic evidence mismatch")

    dispatch = data.get("binary_dispatch_proof", {})
    if set(dispatch.get("required_ledgers", [])) != EXPECTED_LEDGERS:
        fail("dispatch ledgers mismatch")
    if set(dispatch.get("allowed_actions", [])) != EXPECTED_ALLOWED_ACTIONS:
        fail("allowed actions mismatch")
    if set(dispatch.get("rejected_actions", [])) != EXPECTED_REJECTED_ACTIONS:
        fail("rejected actions mismatch")

    print(json.dumps({
        "source_area": data["source_area"],
        "profile": data["profile"],
        "status": "ok"
    }))


if __name__ == "__main__":
    main()
