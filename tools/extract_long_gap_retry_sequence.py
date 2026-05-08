#!/usr/bin/env python3
import json
import sys
from pathlib import Path


ACTIONS = {
    'internal:tcp/handshake',
    'internal:transport/handshake',
    'internal:discovery/request_peers',
    'internal:cluster/request_pre_vote',
    'internal:coordination/fault_detection/follower_check',
    'internal:cluster/coordination/publish_state',
}


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: extract_long_gap_retry_sequence.py <report.json> <after_ms>')

    report = json.loads(Path(sys.argv[1]).read_text())
    after_ms = int(sys.argv[2])
    capture = report.get('steelsearch_transport_capture') or []

    entries = [
        e for e in capture
        if e.get('connection_started_at_ms') is not None
        and e.get('connection_started_at_ms') > after_ms
        and ((e.get('first_frame') or {}).get('action_hint') in ACTIONS)
    ]
    entries.sort(key=lambda e: e.get('connection_started_at_ms'))

    sequence = []
    for entry in entries[:5]:
        sequence.append({
            'peer_addr': entry.get('peer_addr'),
            'connection_started_at_ms': entry.get('connection_started_at_ms'),
            'first_action': (entry.get('first_frame') or {}).get('action_hint'),
            'follow_up_action': (entry.get('follow_up_frame') or {}).get('action_hint'),
            'post_follow_up_action': (entry.get('post_follow_up_frame') or {}).get('action_hint'),
        })

    print(json.dumps({
        'after_ms': after_ms,
        'sequence_count': len(sequence),
        'sequence': sequence,
        'result': 'long_gap_retry_sequence_extracted'
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
