#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        print(json.dumps({'error': 'usage: check_connector_loop_close_listener_cause.py <registration_boundary.json> <connector_loop.json> <lifecycle_matrix.json>'}))
        return 1
    boundary = load(sys.argv[1])
    loop = load(sys.argv[2])
    lifecycle = load(sys.argv[3])

    close_listener_unregisters = bool(boundary.get('close_listener_unregisters_connected_node'))
    repeated_loop = loop.get('result') == 'mixed_runtime_reenters_handshaking_connector_loop_instead_of_settled_connected_nodes_reuse'
    th = lifecycle.get('actions', {}).get('internal:transport/handshake', {})
    transport_handshake_short_remote_eof = bool(th.get('count', 0) > 0 and th.get('all_remote_eof') and th.get('all_sub_threshold'))

    if close_listener_unregisters and repeated_loop and transport_handshake_short_remote_eof:
        result = 'transport_handshake_channel_close_would_immediately_unsettle_any_connected_nodes_registration'
    elif not close_listener_unregisters:
        result = 'close_listener_unregister_contract_not_detected'
    else:
        result = 'close_listener_cause_not_isolated'

    print(json.dumps({
        'close_listener_unregisters_connected_node': close_listener_unregisters,
        'repeated_connector_loop_present': repeated_loop,
        'transport_handshake_short_remote_eof': transport_handshake_short_remote_eof,
        'result': result,
    }))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
