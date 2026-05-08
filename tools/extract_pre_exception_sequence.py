#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: extract_pre_exception_sequence.py <report.json> <before_ms>')

    report = json.loads(Path(sys.argv[1]).read_text())
    before_ms = int(sys.argv[2])
    capture = report.get('steelsearch_transport_capture') or []

    entries = [
        e for e in capture
        if e.get('connection_started_at_ms') is not None
        and e.get('connection_started_at_ms') < before_ms
    ]
    entries.sort(key=lambda e: e.get('connection_started_at_ms'))
    window = entries[-5:]

    sequence = []
    for entry in window:
        sequence.append({
            'peer_addr': entry.get('peer_addr'),
            'connection_started_at_ms': entry.get('connection_started_at_ms'),
            'connection_end_at_ms': entry.get('connection_end_at_ms'),
            'first_action': (entry.get('first_frame') or {}).get('action_hint'),
            'follow_up_action': (entry.get('follow_up_frame') or {}).get('action_hint'),
            'post_follow_up_action': (entry.get('post_follow_up_frame') or {}).get('action_hint'),
            'first_post_response_event': entry.get('first_post_response_event'),
        })

    print(json.dumps({
        'before_ms': before_ms,
        'sequence_count': len(sequence),
        'sequence': sequence,
        'result': 'pre_exception_sequence_extracted'
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
