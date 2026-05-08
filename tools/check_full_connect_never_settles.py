#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        print(json.dumps({'error': 'usage: check_full_connect_never_settles.py <followup_contract.json> <mixed_no_reuse.json> <mixed_report.json>'}))
        return 1
    contract = load(sys.argv[1])
    no_reuse = load(sys.argv[2])
    report = load(sys.argv[3])
    capture = report.get('steelsearch_transport_capture') or []

    source_full_connect_after_probe = bool(
        contract.get('probe_connection_uses_single_reg_channel_profile')
        and contract.get('handshake_success_closes_probe_connection_before_full_connect')
        and contract.get('full_connection_happens_via_transport_service_connect_to_node')
    )
    no_connected_reuse = bool(no_reuse.get('all_coordinator_actions_arrive_as_connection_first_frame'))
    transport_handshake_first = sum(1 for e in capture if (e.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake')

    if source_full_connect_after_probe and no_connected_reuse and transport_handshake_first > 1:
        result = 'full_connect_is_retried_repeatedly_but_never_settles_into_connected_nodes_reuse'
    elif not source_full_connect_after_probe:
        result = 'source_full_connect_after_probe_contract_not_detected'
    else:
        result = 'full_connect_settle_gap_not_isolated'

    print(json.dumps({
        'source_full_connect_after_probe': source_full_connect_after_probe,
        'mixed_no_connected_reuse': no_connected_reuse,
        'transport_handshake_first_frame_count': transport_handshake_first,
        'result': result,
    }))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
