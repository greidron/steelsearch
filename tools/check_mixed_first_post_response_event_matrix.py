#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ACTIONS = [
    'internal:transport/handshake',
    'internal:discovery/request_peers',
    'internal:cluster/request_pre_vote',
    'internal:coordination/fault_detection/follower_check',
    'internal:cluster/coordination/publish_state',
]


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({'error': 'usage: check_mixed_first_post_response_event_matrix.py <mixed_report.json>'}))
        return 1
    report = json.loads(Path(sys.argv[1]).read_text())
    capture = report.get('steelsearch_transport_capture') or []
    actions = {}
    all_remote_eof = True
    for action in ACTIONS:
        entries = [e for e in capture if (e.get('first_frame') or {}).get('action_hint') == action]
        count = len(entries)
        remote = sum(1 for e in entries if e.get('first_post_response_event') == 'remote_eof')
        actions[action] = {'count': count, 'remote_eof_first_post_event_count': remote}
        if count == 0 or remote != count:
            all_remote_eof = False
    result = 'first_post_response_event_remote_eof_for_every_coordinator_socket' if all_remote_eof else 'first_post_response_event_varies_by_action'
    print(json.dumps({'actions': actions, 'result': result}))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
