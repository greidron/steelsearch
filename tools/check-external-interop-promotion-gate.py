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

EXPECTED_ROUTE_REPORTS = {
    "phase-b-gap/<profile>/report.json",
    "interop-handshake-reject-cases.json",
}

EXPECTED_HANDSHAKE_REJECT_CASES = {
    "bad_tcp_handshake_frame": "bad-handshake",
    "unexpected_action_after_handshake": "unexpected-action",
    "wire_version_mismatch_reject": "version-mismatch",
}

EXPECTED_SEMANTIC_EVIDENCE = {
    "named-writeable-roundtrip",
    "cluster-state-diff-apply",
}

EXPECTED_SEMANTIC_REPORTS = {
    "named-writeable-payload-corpus.json",
    "cluster-state-diff-apply-transcript.json",
    "transport-frame-codec-evidence.json",
}

EXPECTED_LEDGERS = {
    "transport-action-subset-ledger.json",
    "transport-negotiation-exception-policy.json",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def fixture_path(name: str) -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    path = repo_root / "tools" / "fixtures" / name
    if not path.exists():
        fail(f"missing fixture report: {name}")
    return path


def validate_named_writeable_corpus(report_name: str) -> None:
    report = json.loads(fixture_path(report_name).read_text(encoding="utf-8"))
    cases = report.get("cases") or []
    if not cases:
        fail("named writeable corpus is empty")
    supported = 0
    unsupported = 0
    for case in cases:
        compatibility = case.get("compatibility")
        expectation = case.get("decode_expectation")
        if compatibility == "supported":
            supported += 1
            if expectation != "decode_and_round_trip" or not case.get("round_trip_hex"):
                fail(f"invalid supported named writeable corpus case: {case.get('case')}")
        elif compatibility == "unsupported":
            unsupported += 1
            if expectation != "fail_closed" or "round_trip_hex" in case:
                fail(f"invalid unsupported named writeable corpus case: {case.get('case')}")
        else:
            fail(f"unknown named writeable compatibility: {compatibility!r}")
        try:
            bytes.fromhex(case["payload_hex"])
        except (KeyError, ValueError) as exc:
            fail(f"invalid named writeable payload hex for {case.get('case')}: {exc}")
    if supported == 0 or unsupported == 0:
        fail("named writeable corpus must include supported and unsupported cases")


def validate_cluster_state_diff_transcript(report_name: str) -> None:
    report = json.loads(fixture_path(report_name).read_text(encoding="utf-8"))
    cases = report.get("cases") or []
    if not cases:
        fail("cluster-state diff apply transcript is empty")
    decoded_and_applied = 0
    rejected_and_preserved = 0
    for case in cases:
        if case.get("publication_mode") != "diff":
            fail(f"non-diff cluster-state transcript case: {case.get('case')}")
        decode_result = case.get("decode_result")
        apply_result = case.get("apply_result")
        if decode_result == "decoded" and apply_result == "applied":
            decoded_and_applied += 1
        elif decode_result == "rejected" and apply_result == "preserved_prior_cache":
            rejected_and_preserved += 1
        else:
            fail(f"invalid cluster-state diff outcome: {case.get('case')}")
    if decoded_and_applied == 0 or rejected_and_preserved == 0:
        fail("cluster-state diff transcript must include applied and rejected cases")


def validate_transport_frame_codec_evidence(report_name: str) -> None:
    report = json.loads(fixture_path(report_name).read_text(encoding="utf-8"))
    if report.get("component") != "os-transport frame codec":
        fail("transport frame codec evidence component mismatch")
    cases = report.get("cases") or []
    expected_cases = {
        "chunked-large-frame",
        "compressed-large-body",
        "large-frame-followed-by-ping",
    }
    observed_cases = {case.get("case") for case in cases}
    if observed_cases != expected_cases:
        fail("transport frame codec evidence cases mismatch")
    source_text = (Path(__file__).resolve().parents[1] / "crates/os-transport/src/frame.rs").read_text(
        encoding="utf-8"
    )
    for case in cases:
        if case.get("result") != "passed":
            fail(f"transport frame codec case is not passed: {case.get('case')}")
        test_name = case.get("rust_test")
        if not test_name or f"fn {test_name}(" not in source_text:
            fail(f"transport frame codec test missing from source: {test_name}")


def validate_handshake_reject_cases(report_name: str) -> None:
    report = json.loads(fixture_path(report_name).read_text(encoding="utf-8"))
    if report.get("name") != "interop-handshake-reject-cases":
        fail("handshake reject fixture name mismatch")
    cases = report.get("cases") or []
    observed = {}
    for case in cases:
        name = case.get("name")
        fixture_class = case.get("class")
        if not name or not fixture_class:
            fail("handshake reject case requires name and class")
        if case.get("expected_decision") != "reject":
            fail(f"handshake reject case is not fail-closed: {name}")
        markers = case.get("expected_markers") or []
        if not markers:
            fail(f"handshake reject case has no expected markers: {name}")
        observed[name] = fixture_class
    if observed != EXPECTED_HANDSHAKE_REJECT_CASES:
        fail("handshake reject cases mismatch")


def validate_semantic_reports(required_reports: set[str]) -> None:
    if required_reports != EXPECTED_SEMANTIC_REPORTS:
        fail("semantic reports mismatch")
    validate_named_writeable_corpus("named-writeable-payload-corpus.json")
    validate_cluster_state_diff_transcript("cluster-state-diff-apply-transcript.json")
    validate_transport_frame_codec_evidence("transport-frame-codec-evidence.json")


def load_transport_action_dispositions(ledger_name: str) -> tuple[set[str], set[str]]:
    ledger = json.loads(fixture_path(ledger_name).read_text(encoding="utf-8"))
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
    ledger = json.loads(fixture_path(ledger_name).read_text(encoding="utf-8"))
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
    if set(route.get("required_reports", [])) != EXPECTED_ROUTE_REPORTS:
        fail("route reports mismatch")
    if set(route.get("required_evidence_classes", [])) != EXPECTED_ROUTE_EVIDENCE:
        fail("route evidence mismatch")
    validate_handshake_reject_cases("interop-handshake-reject-cases.json")
    validate_semantic_reports(set(semantic.get("required_reports", [])))
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
