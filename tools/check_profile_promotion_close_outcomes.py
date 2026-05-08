#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            'usage: check_profile_promotion_close_outcomes.py <promotion_gap.json> <tail_case.json>'
        )

    promotion = load(sys.argv[1])
    tail = load(sys.argv[2])

    promotion_established = (
        promotion.get('source_has_default_multi_channel_profile') is True
        and promotion.get('all_no_follow_up_or_post') is True
        and promotion.get('all_remote_eof_first_post') is True
        and promotion.get('all_hold_open_started') is True
    )
    dominant_restart_path = tail.get('non_restart_count') == 1 and tail.get('direct_full_connect_socket_count', 0) > 1
    exception_not_tail = tail.get('terminal_tail_case') is False

    result = (
        'profile_promotion_pre_reuse_peer_close_trigger_established_with_dominant_restart_loop_and_one_non_tail_exception'
        if promotion_established and dominant_restart_path and exception_not_tail
        else 'profile_promotion_close_outcomes_not_fully_established'
    )

    print(json.dumps({
        'promotion_gap_established': promotion_established,
        'direct_full_connect_socket_count': tail.get('direct_full_connect_socket_count'),
        'non_restart_count': tail.get('non_restart_count'),
        'exception_not_tail': exception_not_tail,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
