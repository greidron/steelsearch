#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: extract_probe_retry_gap_paths.py <report.json> <immediate_threshold_ms>')

    report = json.loads(Path(sys.argv[1]).read_text())
    threshold = int(sys.argv[2])
    capture = report.get('steelsearch_transport_capture') or []

    direct = [
        e for e in capture
        if ((e.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake')
    ]

    immediate = []
    delayed = []
    for entry in direct:
        end_at = entry.get('connection_end_at_ms')
        later_tcp = [
            other for other in capture
            if other is not entry
            and ((other.get('first_frame') or {}).get('action_hint') == 'internal:tcp/handshake')
            and other.get('connection_started_at_ms') is not None
            and end_at is not None
            and other.get('connection_started_at_ms') > end_at
        ]
        if not later_tcp:
            continue
        first_later = min(later_tcp, key=lambda e: e.get('connection_started_at_ms'))
        gap = first_later.get('connection_started_at_ms') - end_at
        summary = {
            'peer_addr': entry.get('peer_addr'),
            'connection_end_at_ms': end_at,
            'next_tcp_started_at_ms': first_later.get('connection_started_at_ms'),
            'gap_ms': gap,
        }
        if gap <= threshold:
            immediate.append(summary)
        else:
            delayed.append(summary)

    print(json.dumps({
        'immediate_threshold_ms': threshold,
        'immediate_count': len(immediate),
        'delayed_count': len(delayed),
        'delayed_entries': delayed,
        'result': 'probe_retry_gap_paths_split'
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
