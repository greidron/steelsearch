#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"error": "usage: check_state_channel_acceptance_gap.py <state_channel_contract.json> <normalized_publication_baseline.json>"}))
        return 1

    contract = load(sys.argv[1])
    baseline = load(sys.argv[2])

    reusable_state_contract = bool(
        contract.get("publish_state_uses_state_request_options")
        and contract.get("transport_service_send_request_uses_get_connection")
        and contract.get("transport_service_get_connection_uses_connection_manager")
        and contract.get("default_connection_profile_has_state_bucket")
    )

    reference = baseline.get("reference", {})
    mixed = baseline.get("mixed", {})

    reference_retained = reference.get("state_channel_retention_class") == "retained_through_commit"
    mixed_failed = mixed.get("state_channel_retention_class") == "same_tick_remote_eof_before_commit"

    if reusable_state_contract and reference_retained and mixed_failed:
        result = "reusable_state_channel_contract_holds_in_reference_but_fails_in_mixed_acceptance"
    elif not reusable_state_contract:
        result = "state_channel_contract_not_detected"
    else:
        result = "baseline_insufficient_to_isolate_state_channel_acceptance_gap"

    print(json.dumps({
        "reusable_state_channel_contract": reusable_state_contract,
        "reference_state_channel_retention_class": reference.get("state_channel_retention_class"),
        "mixed_state_channel_retention_class": mixed.get("state_channel_retention_class"),
        "reference_publication_progress_class": reference.get("publication_progress_class"),
        "mixed_publication_progress_class": mixed.get("publication_progress_class"),
        "result": result,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
