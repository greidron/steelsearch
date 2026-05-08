#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(
            'usage: check_direct_full_connect_hold_open_peer_close.py <report.json>'
        )

    report = json.loads(Path(sys.argv[1]).read_text())
    capture = report.get('steelsearch_transport_capture') or []
    entries = [
        e for e in capture
        if ((e.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake')
    ]

    all_hold_open_started = bool(entries) and all(e.get('hold_open_started_at_ms') is not None for e in entries)
    all_no_follow_up_or_post = bool(entries) and all(
        e.get('follow_up_frame') is None and e.get('post_follow_up_frame') is None
        for e in entries
    )
    all_remote_eof_first_post = bool(entries) and all(
        e.get('first_post_response_event') == 'remote_eof' for e in entries
    )
    all_peer_closed_after_local_hold_open = bool(entries) and all(
        e.get('response_frame_sent_at_ms') is not None
        and e.get('hold_open_started_at_ms') is not None
        and e.get('hold_open_started_at_ms') >= e.get('response_frame_sent_at_ms')
        and e.get('connection_end') == 'remote_eof'
        for e in entries
    )

    result = (
        'direct_full_connect_socket_enters_local_hold_open_but_peer_still_closes_before_any_post_handshake_request'
        if all_hold_open_started
        and all_no_follow_up_or_post
        and all_remote_eof_first_post
        and all_peer_closed_after_local_hold_open
        else 'direct_full_connect_hold_open_peer_close_not_fully_established'
    )

    print(json.dumps({
        'direct_full_connect_socket_count': len(entries),
        'all_hold_open_started': all_hold_open_started,
        'all_no_follow_up_or_post': all_no_follow_up_or_post,
        'all_remote_eof_first_post': all_remote_eof_first_post,
        'all_peer_closed_after_local_hold_open': all_peer_closed_after_local_hold_open,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
