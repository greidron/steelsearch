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
    if len(sys.argv) != 3:
        print(json.dumps({'error': 'usage: check_mixed_socket_lifecycle_window_matrix.py <mixed_report.json> <threshold_ms>'}))
        return 1
    report = json.loads(Path(sys.argv[1]).read_text())
    threshold = int(sys.argv[2])
    capture = report.get('steelsearch_transport_capture') or []
    actions = {}
    all_sub_threshold = True
    for action in ACTIONS:
        entries = [e for e in capture if (e.get('first_frame') or {}).get('action_hint') == action]
        windows = []
        for e in entries:
            sent = e.get('response_frame_sent_at_ms')
            end = e.get('connection_end_at_ms')
            if sent is not None and end is not None:
                windows.append(int(end) - int(sent))
        action_info = {
            'count': len(entries),
            'min_window_ms': min(windows) if windows else None,
            'max_window_ms': max(windows) if windows else None,
            'all_remote_eof': all(e.get('connection_end') == 'remote_eof' for e in entries) if entries else False,
            'all_sub_threshold': all(w < threshold for w in windows) if windows else False,
        }
        actions[action] = action_info
        if not entries or not action_info['all_remote_eof'] or not action_info['all_sub_threshold']:
            all_sub_threshold = False
    result = 'coordinator_sockets_are_uniform_one_shot_sub_threshold_remote_eof_lifecycle' if all_sub_threshold else 'socket_lifecycle_varies_by_action'
    print(json.dumps({'threshold_ms': threshold, 'actions': actions, 'result': result}))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
