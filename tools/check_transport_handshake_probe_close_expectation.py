#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({'error': 'usage: check_transport_handshake_probe_close_expectation.py <followup_contract.json> <mixed_report.json>'}))
        return 1
    contract = load(sys.argv[1])
    report = load(sys.argv[2])
    capture = report.get('steelsearch_transport_capture') or []

    source_probe_close_expected = bool(
        contract.get('probe_connection_uses_single_reg_channel_profile')
        and contract.get('handshake_success_closes_probe_connection_before_full_connect')
        and contract.get('full_connection_happens_via_transport_service_connect_to_node')
    )

    entries = [e for e in capture if (e.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake']
    count = len(entries)
    all_identity_then_remote_eof = count > 0 and all(
        e.get('response_frame') is not None
        and e.get('first_post_response_event') == 'remote_eof'
        and e.get('connection_end') == 'remote_eof'
        for e in entries
    )

    if source_probe_close_expected and all_identity_then_remote_eof:
        result = 'transport_handshake_remote_eof_matches_expected_probe_close_before_full_connect'
    elif not source_probe_close_expected:
        result = 'source_probe_close_contract_not_detected'
    else:
        result = 'transport_handshake_remote_eof_not_explained_by_probe_close_contract'

    print(json.dumps({
        'source_probe_close_expected': source_probe_close_expected,
        'transport_handshake_first_frame_count': count,
        'all_identity_then_remote_eof': all_identity_then_remote_eof,
        'result': result,
    }))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
