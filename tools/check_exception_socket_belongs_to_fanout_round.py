#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_exception_socket_belongs_to_fanout_round.py <pre_exception_sequence.json> <exception_start_ms> <tolerance_ms>')

    seq = load(sys.argv[1]).get('sequence') or []
    exception_start_ms = int(sys.argv[2])
    tolerance_ms = int(sys.argv[3])

    same_round_entries = [
        e for e in seq
        if e.get('connection_started_at_ms') is not None
        and abs(e.get('connection_started_at_ms') - exception_start_ms) <= tolerance_ms
    ]
    request_peers_same_round = [e for e in same_round_entries if e.get('first_action') == 'internal:discovery/request_peers']
    tcp_same_round = [e for e in same_round_entries if e.get('first_action') == 'internal:tcp/handshake']

    result = (
        'exception_socket_start_time_belongs_to_same_discovery_fanout_round_as_request_peers_burst'
        if len(request_peers_same_round) >= 1 and len(tcp_same_round) >= 1
        else 'exception_socket_not_clearly_matched_to_same_fanout_round'
    )

    print(json.dumps({
        'exception_start_ms': exception_start_ms,
        'tolerance_ms': tolerance_ms,
        'same_round_entry_count': len(same_round_entries),
        'same_round_request_peers_count': len(request_peers_same_round),
        'same_round_tcp_handshake_count': len(tcp_same_round),
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
