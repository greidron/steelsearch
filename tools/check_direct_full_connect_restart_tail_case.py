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
            'usage: check_direct_full_connect_restart_tail_case.py <report.json>'
        )

    report = json.loads(Path(sys.argv[1]).read_text())
    capture = report.get('steelsearch_transport_capture') or []

    direct = [
        e for e in capture
        if ((e.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake')
    ]

    without_restart = []
    max_started = max((e.get('connection_started_at_ms') or -1) for e in capture) if capture else -1
    max_ended = max((e.get('connection_end_at_ms') or -1) for e in capture) if capture else -1

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
        if not later:
            without_restart.append(entry)

    terminal_tail_case = (
        len(without_restart) == 1
        and without_restart[0].get('connection_end_at_ms') == max_ended
        and without_restart[0].get('connection_started_at_ms') == max_started
    )

    result = (
        'sole_non_restart_direct_full_connect_socket_is_terminal_capture_tail'
        if terminal_tail_case
        else 'non_restart_direct_full_connect_socket_not_explained_as_terminal_tail'
    )

    print(json.dumps({
        'direct_full_connect_socket_count': len(direct),
        'non_restart_count': len(without_restart),
        'terminal_tail_case': terminal_tail_case,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
