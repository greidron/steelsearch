#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_single_peer_loop_settle_loss_point.py <trace_direct_multiplicity.json> <report.json>')

    trace = load(sys.argv[1])
    report = load(sys.argv[2])
    capture = report.get('steelsearch_transport_capture') or []

    single_remote_peer = (
        trace.get('result') == 'current_blocker_is_better_reframed_as_single_remote_peer_repeated_one_shot_connection_loop_than_as_multi_address_alias_multiplicity'
    )

    direct_full_connect = [
        e for e in capture
        if (e.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake'
    ]
    closes_before_post_request = [
        e for e in direct_full_connect
        if e.get('first_post_response_event') == 'remote_eof'
        and e.get('post_follow_up_frame') is None
    ]

    result = (
        'single_peer_one_shot_loop_loses_settle_at_direct_full_connect_transport_handshake_remote_eof_before_any_post_handshake_request'
        if single_remote_peer and direct_full_connect and len(closes_before_post_request) == len(direct_full_connect)
        else 'single_peer_loop_settle_loss_point_not_fully_established'
    )

    print(json.dumps({
        'single_remote_peer': single_remote_peer,
        'direct_full_connect_count': len(direct_full_connect),
        'closes_before_post_request_count': len(closes_before_post_request),
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
