#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            'usage: check_direct_full_connect_profile_promotion_gap.py <ConnectionProfile.java> <report.json>'
        )

    source = Path(sys.argv[1]).read_text()
    report = json.loads(Path(sys.argv[2]).read_text())

    source_has_default_multi_channel_profile = 'buildDefaultConnectionProfile' in source and all(
        token in source
        for token in [
            'TransportRequestOptions.Type.BULK',
            'TransportRequestOptions.Type.PING',
            'TransportRequestOptions.Type.STATE',
            'TransportRequestOptions.Type.RECOVERY',
            'TransportRequestOptions.Type.REG',
        ]
    )

    capture = report.get('steelsearch_transport_capture') or []
    direct = [
        e for e in capture
        if ((e.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake')
    ]

    all_no_follow_up_or_post = bool(direct) and all(
        e.get('follow_up_frame') is None and e.get('post_follow_up_frame') is None
        for e in direct
    )
    all_remote_eof_first_post = bool(direct) and all(
        e.get('first_post_response_event') == 'remote_eof' for e in direct
    )
    all_hold_open_started = bool(direct) and all(e.get('hold_open_started_at_ms') is not None for e in direct)

    result = (
        'direct_full_connect_sockets_close_before_default_multi_channel_profile_promotion_or_reuse'
        if source_has_default_multi_channel_profile
        and all_no_follow_up_or_post
        and all_remote_eof_first_post
        and all_hold_open_started
        else 'direct_full_connect_profile_promotion_gap_not_fully_established'
    )

    print(json.dumps({
        'source_has_default_multi_channel_profile': source_has_default_multi_channel_profile,
        'direct_full_connect_socket_count': len(direct),
        'all_no_follow_up_or_post': all_no_follow_up_or_post,
        'all_remote_eof_first_post': all_remote_eof_first_post,
        'all_hold_open_started': all_hold_open_started,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
