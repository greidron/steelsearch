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


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(
            'usage: check_direct_full_connect_close_restarts_fresh_socket_loop.py <report.json>'
        )

    report = json.loads(Path(sys.argv[1]).read_text())
    capture = report.get('steelsearch_transport_capture') or []

    direct = [
        e for e in capture
        if ((e.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake')
    ]

    restart_count = 0
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
        if later:
            restart_count += 1

    all_remote_eof = bool(direct) and all(e.get('connection_end') == 'remote_eof' for e in direct)
    all_restart = bool(direct) and restart_count == len(direct)

    result = (
        'direct_full_connect_close_is_followed_by_fresh_socket_connector_loop_restart'
        if all_remote_eof and all_restart
        else 'direct_full_connect_restart_loop_not_fully_established'
    )

    print(json.dumps({
        'direct_full_connect_socket_count': len(direct),
        'all_remote_eof': all_remote_eof,
        'restart_count': restart_count,
        'all_restart_into_fresh_socket_loop': all_restart,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
