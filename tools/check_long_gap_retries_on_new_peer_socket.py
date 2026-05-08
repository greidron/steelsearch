#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_long_gap_retries_on_new_peer_socket.py <report.json> <peer_addr>')

    report = json.loads(Path(sys.argv[1]).read_text())
    peer_addr = sys.argv[2]
    capture = report.get('steelsearch_transport_capture') or []

    exception_entries = [e for e in capture if e.get('peer_addr') == peer_addr]
    if len(exception_entries) != 1:
        print(json.dumps({'error': 'expected exactly one exception peer entry', 'count': len(exception_entries)}))
        return 1

    exception_entry = exception_entries[0]
    end_at = exception_entry.get('connection_end_at_ms')
    later_tcp = [
        e for e in capture
        if ((e.get('first_frame') or {}).get('action_hint') == 'internal:tcp/handshake')
        and e.get('connection_started_at_ms') is not None
        and end_at is not None
        and e.get('connection_started_at_ms') > end_at
    ]
    first_later = min(later_tcp, key=lambda e: e.get('connection_started_at_ms')) if later_tcp else None
    retries_on_new_peer_socket = first_later is not None and first_later.get('peer_addr') != peer_addr

    print(json.dumps({
        'exception_peer_addr': peer_addr,
        'next_tcp_peer_addr': first_later.get('peer_addr') if first_later else None,
        'next_tcp_started_at_ms': first_later.get('connection_started_at_ms') if first_later else None,
        'retries_on_new_peer_socket': retries_on_new_peer_socket,
        'result': 'long_gap_exception_retries_via_new_peer_socket' if retries_on_new_peer_socket else 'long_gap_exception_retry_socket_reuse_not_established'
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
