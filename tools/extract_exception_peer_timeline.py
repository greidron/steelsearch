#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: extract_exception_peer_timeline.py <report.json> <peer_addr>')

    report = json.loads(Path(sys.argv[1]).read_text())
    peer_addr = sys.argv[2]
    capture = report.get('steelsearch_transport_capture') or []

    entries = [e for e in capture if e.get('peer_addr') == peer_addr]
    entries.sort(key=lambda e: (e.get('connection_started_at_ms') or -1, e.get('connection_end_at_ms') or -1))

    timeline = []
    for entry in entries:
        timeline.append({
            'connection_started_at_ms': entry.get('connection_started_at_ms'),
            'connection_end_at_ms': entry.get('connection_end_at_ms'),
            'first_action': (entry.get('first_frame') or {}).get('action_hint'),
            'follow_up_action': (entry.get('follow_up_frame') or {}).get('action_hint'),
            'post_follow_up_action': (entry.get('post_follow_up_frame') or {}).get('action_hint'),
            'first_post_response_event': entry.get('first_post_response_event'),
            'connection_end': entry.get('connection_end'),
        })

    print(json.dumps({
        'peer_addr': peer_addr,
        'entry_count': len(timeline),
        'timeline': timeline,
        'result': 'exception_peer_timeline_extracted'
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
