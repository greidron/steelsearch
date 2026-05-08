#!/usr/bin/env python3
import json
import sys
from collections import Counter
from pathlib import Path

REQUIRED_ACTIONS = [
    'internal:transport/handshake',
    'internal:discovery/request_peers',
    'internal:cluster/request_pre_vote',
    'internal:cluster/coordination/start_join',
    'internal:cluster/coordination/publish_state',
]


def load_json(path: str):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def count_events(report):
    caps = report.get('steelsearch_transport_capture') or []
    return {
        'follow_up_frames': sum(1 for e in caps if e.get('follow_up_frame')),
        'post_follow_up_frames': sum(1 for e in caps if e.get('post_follow_up_frame')),
        'proactive_keepalive_total': sum(int(e.get('proactive_keepalive_count') or 0) for e in caps),
        'first_post_response_event': Counter(e.get('first_post_response_event') for e in caps),
        'connection_end': Counter(e.get('connection_end') for e in caps),
    }


def main() -> int:
    if len(sys.argv) != 4:
        print('usage: check_current_baseline_stops_before_followup_handler.py <main.rs> <old-formed-report.json> <current-baseline-report.json>', file=sys.stderr)
        return 2

    source = Path(sys.argv[1]).read_text(encoding='utf-8')
    old = load_json(sys.argv[2])
    current = load_json(sys.argv[3])

    source_has_actions = all(action in source for action in REQUIRED_ACTIONS)
    old_counts = count_events(old)
    current_counts = count_events(current)

    print(f'source_has_followup_actions={source_has_actions}')
    print(f"old_follow_up_frames={old_counts['follow_up_frames']}")
    print(f"current_follow_up_frames={current_counts['follow_up_frames']}")
    print(f"old_post_follow_up_frames={old_counts['post_follow_up_frames']}")
    print(f"current_post_follow_up_frames={current_counts['post_follow_up_frames']}")
    print(f"old_proactive_keepalive_total={old_counts['proactive_keepalive_total']}")
    print(f"current_proactive_keepalive_total={current_counts['proactive_keepalive_total']}")
    print(f"old_first_post_response_event={dict(old_counts['first_post_response_event'])}")
    print(f"current_first_post_response_event={dict(current_counts['first_post_response_event'])}")
    print(f"old_connection_end={dict(old_counts['connection_end'])}")
    print(f"current_connection_end={dict(current_counts['connection_end'])}")

    if (
        source_has_actions
        and old_counts['follow_up_frames'] > 0
        and old_counts['post_follow_up_frames'] > 0
        and current_counts['follow_up_frames'] == 0
        and current_counts['post_follow_up_frames'] == 0
        and current_counts['first_post_response_event'].get('idle_timeout', 0) > 0
        and current_counts['proactive_keepalive_total'] > old_counts['proactive_keepalive_total']
    ):
        print('result=current_baseline_stops_before_followup_frame_arrival_or_handler_dispatch_not_at_missing_followup_action_implementation')
        return 0

    print('result=followup_handler_boundary_not_yet_decisive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
