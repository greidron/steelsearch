#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({'error': 'usage: check_mixed_repeated_connector_loop.py <followup_contract.json> <mixed_report.json>'}))
        return 1
    contract = load(sys.argv[1])
    report = load(sys.argv[2])
    capture = report.get('steelsearch_transport_capture') or []

    source_connector_contract = bool(
        contract.get('probe_connection_uses_single_reg_channel_profile')
        and contract.get('handshake_success_closes_probe_connection_before_full_connect')
        and contract.get('full_connection_happens_via_transport_service_connect_to_node')
    )

    tcp_handshake_first = sum(1 for e in capture if (e.get('first_frame') or {}).get('action_hint') == 'internal:tcp/handshake')
    transport_handshake_first = sum(1 for e in capture if (e.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake')
    request_peers_first = sum(1 for e in capture if (e.get('first_frame') or {}).get('action_hint') == 'internal:discovery/request_peers')

    repeated_connector_loop = tcp_handshake_first > 1 and transport_handshake_first > 1 and request_peers_first > 1

    if source_connector_contract and repeated_connector_loop:
        result = 'mixed_runtime_reenters_handshaking_connector_loop_instead_of_settled_connected_nodes_reuse'
    elif not source_connector_contract:
        result = 'source_connector_contract_not_detected'
    else:
        result = 'repeated_connector_loop_not_isolated'

    print(json.dumps({
        'source_connector_contract_present': source_connector_contract,
        'tcp_handshake_first_frame_count': tcp_handshake_first,
        'transport_handshake_first_frame_count': transport_handshake_first,
        'request_peers_first_frame_count': request_peers_first,
        'result': result,
    }))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
