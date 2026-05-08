#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 6:
        print(json.dumps({"error": "usage: check_registration_gap_cause.py <validator_contract.json> <mixed_followup.json> <mixed_no_reuse.json> <transport_end.json> <transport_window.json>"}))
        return 1

    validator = load(sys.argv[1])
    followup = load(sys.argv[2])
    noreuse = load(sys.argv[3])
    tend = load(sys.argv[4])
    twindow = load(sys.argv[5])

    validator_contract_present = bool(
        validator.get('validator_failure_closes_connection')
        and validator.get('validator_failure_fails_connection_listeners')
        and validator.get('registration_happens_only_in_validator_success_branch')
    )
    followup_failure_cleared = not bool(followup.get('completed_handshake_followup_failed')) and not bool(followup.get('connection_reset'))
    no_reuse = bool(noreuse.get('all_coordinator_actions_arrive_as_connection_first_frame'))
    identity_remote_eof = int(tend.get('remote_eof_after_identity_count', 0)) == int(tend.get('transport_handshake_count', -1)) and int(tend.get('transport_handshake_count', 0)) > 0
    quick_close = int(twindow.get('max_window_ms', 10**9)) < int(twindow.get('threshold_ms', 1000))

    if validator_contract_present and followup_failure_cleared and no_reuse and identity_remote_eof and quick_close:
        result = 'socket_lifecycle_or_close_ordering_after_identity_response_is_more_direct_cause_than_validator_failure'
    elif not validator_contract_present:
        result = 'validator_contract_not_detected'
    else:
        result = 'registration_gap_cause_not_isolated'

    print(json.dumps({
        'validator_contract_present': validator_contract_present,
        'mixed_followup_failure_cleared': followup_failure_cleared,
        'mixed_no_reusable_channel': no_reuse,
        'identity_response_always_followed_by_remote_eof': identity_remote_eof,
        'followup_channel_closes_sub_threshold': quick_close,
        'result': result,
    }))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
