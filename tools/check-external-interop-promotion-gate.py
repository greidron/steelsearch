#!/usr/bin/env python3
import json
import sys
from pathlib import Path


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

EXPECTED_LEDGERS = {
    "transport-action-subset-ledger.json",
    "transport-negotiation-exception-policy.json",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def load_transport_action_dispositions(ledger_name: str) -> tuple[set[str], set[str]]:
    repo_root = Path(__file__).resolve().parents[1]
    ledger_path = repo_root / "tools" / "fixtures" / ledger_name
    if not ledger_path.exists():
        fail(f"missing transport action ledger: {ledger_name}")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    allowed = set()
    rejected = set()
    for case in ledger.get("cases", []):
        action = case.get("action")
        disposition = case.get("disposition")
        if not action:
            continue
        if disposition == "allowed":
            allowed.add(action)
        elif disposition == "rejected":
            rejected.add(action)
        else:
            fail(f"unknown transport action disposition for {action}: {disposition}")
    return allowed, rejected


def load_negotiation_action_dispositions(ledger_name: str) -> tuple[set[str], set[str]]:
    repo_root = Path(__file__).resolve().parents[1]
    ledger_path = repo_root / "tools" / "fixtures" / ledger_name
    if not ledger_path.exists():
        fail(f"missing transport negotiation ledger: {ledger_name}")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    allowed = set()
    rejected = set()
    for case in ledger.get("cases", []):
        if case.get("category") != "action_classification":
            continue
        action = case.get("kind")
        disposition = case.get("disposition")
        if not action or action == "unknown_transport_action":
            continue
        if disposition == "allowed":
            allowed.add(action)
        elif disposition == "rejected":
            rejected.add(action)
        else:
            fail(f"unknown transport negotiation disposition for {action}: {disposition}")
    return allowed, rejected


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
    allowed_actions, rejected_actions = load_transport_action_dispositions(
        "transport-action-subset-ledger.json"
    )
    if set(dispatch.get("allowed_actions", [])) != allowed_actions:
        fail("allowed actions mismatch with transport-action-subset-ledger.json")
    if set(dispatch.get("rejected_actions", [])) != rejected_actions:
        fail("rejected actions mismatch with transport-action-subset-ledger.json")
    if set(dispatch.get("allowed_actions", [])) & set(dispatch.get("rejected_actions", [])):
        fail("rejected actions mismatch")
    negotiation_allowed, negotiation_rejected = load_negotiation_action_dispositions(
        "transport-negotiation-exception-policy.json"
    )
    if negotiation_allowed != allowed_actions:
        fail("allowed actions mismatch with transport-negotiation-exception-policy.json")
    if negotiation_rejected != rejected_actions:
        fail("rejected actions mismatch with transport-negotiation-exception-policy.json")

    print(json.dumps({
        "source_area": data["source_area"],
        "profile": data["profile"],
        "status": "ok"
    }))


if __name__ == "__main__":
    main()
