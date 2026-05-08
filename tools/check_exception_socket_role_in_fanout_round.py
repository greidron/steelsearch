#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_exception_socket_role_in_fanout_round.py <report.json> <exception_start_ms> <tolerance_ms>')

    report = json.loads(Path(sys.argv[1]).read_text())
    exception_start_ms = int(sys.argv[2])
    tolerance_ms = int(sys.argv[3])
    capture = report.get('steelsearch_transport_capture') or []

    same_round = [
        e for e in capture
        if e.get('connection_started_at_ms') is not None
        and abs(e.get('connection_started_at_ms') - exception_start_ms) <= tolerance_ms
    ]

    direct_full_connect = [e for e in same_round if (e.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake']
    tcp = [e for e in same_round if (e.get('first_frame') or {}).get('action_hint') == 'internal:tcp/handshake']
    request_peers = [e for e in same_round if (e.get('first_frame') or {}).get('action_hint') == 'internal:discovery/request_peers']

    result = (
        'exception_socket_is_unique_direct_full_connect_member_inside_same_peerfinder_fanout_round'
        if len(direct_full_connect) == 1 and len(tcp) >= 1 and len(request_peers) >= 3
        else 'exception_socket_role_in_fanout_round_not_fully_established'
    )

    print(json.dumps({
        'same_round_count': len(same_round),
        'same_round_tcp_count': len(tcp),
        'same_round_request_peers_count': len(request_peers),
        'same_round_direct_full_connect_count': len(direct_full_connect),
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
