#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_long_gap_retry_is_capture_tail.py <report.json> <peer_addr>')

    report = json.loads(Path(sys.argv[1]).read_text())
    peer_addr = sys.argv[2]
    capture = report.get('steelsearch_transport_capture') or []
    if not capture:
        print(json.dumps({'error': 'empty capture'}))
        return 1

    sorted_entries = sorted(capture, key=lambda e: (e.get('connection_started_at_ms') or -1, e.get('connection_end_at_ms') or -1))
    last_entry = sorted_entries[-1]
    is_capture_tail = last_entry.get('peer_addr') == peer_addr and ((last_entry.get('first_frame') or {}).get('action_hint') == 'internal:tcp/handshake')

    print(json.dumps({
        'peer_addr': peer_addr,
        'last_entry_peer_addr': last_entry.get('peer_addr'),
        'last_entry_first_action': (last_entry.get('first_frame') or {}).get('action_hint'),
        'is_capture_tail': is_capture_tail,
        'result': 'long_gap_retry_sequence_is_capture_tail' if is_capture_tail else 'long_gap_retry_sequence_not_capture_tail'
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
