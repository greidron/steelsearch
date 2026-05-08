#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({'error': 'usage: check_transport_handshake_unsettle_trigger.py <registration_boundary.json> <mixed_report.json>'}))
        return 1
    boundary = load(sys.argv[1])
    report = load(sys.argv[2])
    capture = report.get('steelsearch_transport_capture') or []

    close_listener_unregisters = bool(boundary.get('close_listener_unregisters_connected_node'))
    entries = [e for e in capture if (e.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake']
    count = len(entries)
    all_identity_response_then_remote_eof = count > 0 and all(
        e.get('response_frame') is not None
        and e.get('first_post_response_event') == 'remote_eof'
        and e.get('connection_end') == 'remote_eof'
        for e in entries
    )

    if close_listener_unregisters and all_identity_response_then_remote_eof:
        result = 'transport_handshake_identity_response_then_remote_eof_is_direct_unsettle_trigger_for_any_connected_nodes_registration'
    elif not close_listener_unregisters:
        result = 'close_listener_unregister_contract_not_detected'
    else:
        result = 'transport_handshake_unsettle_trigger_not_isolated'

    print(json.dumps({
        'close_listener_unregisters_connected_node': close_listener_unregisters,
        'transport_handshake_first_frame_count': count,
        'all_identity_response_then_remote_eof': all_identity_response_then_remote_eof,
        'result': result,
    }))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
