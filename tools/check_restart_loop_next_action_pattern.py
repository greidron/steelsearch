#!/usr/bin/env python3
import json
import sys
from collections import Counter
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
    if len(sys.argv) != 2:
        raise SystemExit('usage: check_restart_loop_next_action_pattern.py <report.json>')

    report = json.loads(Path(sys.argv[1]).read_text())
    capture = report.get('steelsearch_transport_capture') or []

    direct = [
        e for e in capture
        if ((e.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake')
    ]

    next_actions = []
    for entry in direct:
        end_at = entry.get('connection_end_at_ms')
        if end_at is None:
            continue
        later = [
            other for other in capture
            if other is not entry
            and other.get('connection_started_at_ms') is not None
            and other.get('connection_started_at_ms') > end_at
            and ((other.get('first_frame') or {}).get('action_hint') in ACTIONS)
        ]
        if not later:
            continue
        first_later = min(later, key=lambda e: e.get('connection_started_at_ms'))
        next_actions.append((first_later.get('first_frame') or {}).get('action_hint'))

    counts = Counter(next_actions)
    total = sum(counts.values())
    dominant = counts.most_common(1)[0][0] if counts else None
    dominant_count = counts.most_common(1)[0][1] if counts else 0

    result = (
        'restart_loop_next_action_pattern_extracted'
        if total > 0
        else 'restart_loop_next_action_pattern_not_observed'
    )

    print(json.dumps({
        'restart_observation_count': total,
        'next_action_counts': dict(counts),
        'dominant_next_action': dominant,
        'dominant_next_action_count': dominant_count,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
