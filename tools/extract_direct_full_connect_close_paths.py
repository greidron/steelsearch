#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ACTIONS = {
    'internal:transport/handshake',
    'internal:discovery/request_peers',
    'internal:cluster/request_pre_vote',
    'internal:coordination/fault_detection/follower_check',
    'internal:cluster/coordination/publish_state',
}


def summarize(entry):
    first = entry.get('first_frame') or {}
    response = entry.get('response_frame') or {}
    return {
        'peer_addr': entry.get('peer_addr'),
        'connection_started_at_ms': entry.get('connection_started_at_ms'),
        'connection_end_at_ms': entry.get('connection_end_at_ms'),
        'connection_end': entry.get('connection_end'),
        'first_action': first.get('action_hint'),
        'response_message_length': response.get('message_length'),
        'first_post_response_event': entry.get('first_post_response_event'),
    }


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit('usage: extract_direct_full_connect_close_paths.py <report.json>')

    report = json.loads(Path(sys.argv[1]).read_text())
    capture = report.get('steelsearch_transport_capture') or []

    direct = [
        e for e in capture
        if ((e.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake')
    ]

    restart = []
    exception = []
    for entry in direct:
        end_at = entry.get('connection_end_at_ms')
        later = [
            other for other in capture
            if other is not entry
            and other.get('connection_started_at_ms') is not None
            and end_at is not None
            and other.get('connection_started_at_ms') > end_at
            and ((other.get('first_frame') or {}).get('action_hint') in ACTIONS)
        ]
        if later:
            restart.append(summarize(entry))
        else:
            exception.append(summarize(entry))

    result = 'direct_full_connect_close_paths_split_into_restart_and_exception'
    print(json.dumps({
        'direct_full_connect_socket_count': len(direct),
        'restart_loop_count': len(restart),
        'exception_path_count': len(exception),
        'exception_entries': exception,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
