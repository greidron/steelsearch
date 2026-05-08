#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            'usage: check_direct_full_connect_pre_second_frame_close.py <validator_check.json> <report.json>'
        )

    validator = json.loads(Path(sys.argv[1]).read_text())
    report = json.loads(Path(sys.argv[2]).read_text())

    capture = report.get('steelsearch_transport_capture') or []
    entries = [
        e for e in capture
        if ((e.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake')
    ]

    all_no_follow_up_frame = bool(entries) and all(e.get('follow_up_frame') is None for e in entries)
    all_no_post_follow_up_frame = bool(entries) and all(e.get('post_follow_up_frame') is None for e in entries)
    all_remote_eof_first_post_event = bool(entries) and all(
        e.get('first_post_response_event') == 'remote_eof' for e in entries
    )
    all_identity_response_then_remote_eof = bool(entries) and all(
        e.get('response_frame') is not None and e.get('connection_end') == 'remote_eof'
        for e in entries
    )

    validator_ruled_out = (
        validator.get('source_validator_checks_node_equals_remote') is True
        and validator.get('identity_equivalent') is True
    )

    result = (
        'direct_full_connect_socket_closes_before_any_second_frame_so_next_gap_is_pre_second_frame_non_identity_trigger'
        if validator_ruled_out
        and all_no_follow_up_frame
        and all_no_post_follow_up_frame
        and all_remote_eof_first_post_event
        and all_identity_response_then_remote_eof
        else 'direct_full_connect_pre_second_frame_close_not_fully_established'
    )

    print(json.dumps({
        'validator_ruled_out': validator_ruled_out,
        'direct_full_connect_socket_count': len(entries),
        'all_no_follow_up_frame': all_no_follow_up_frame,
        'all_no_post_follow_up_frame': all_no_post_follow_up_frame,
        'all_remote_eof_first_post_event': all_remote_eof_first_post_event,
        'all_identity_response_then_remote_eof': all_identity_response_then_remote_eof,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
