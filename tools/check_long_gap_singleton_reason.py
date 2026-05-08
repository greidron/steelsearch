#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_long_gap_singleton_reason.py <retry_gap_paths.json> <exception_round_role.json>')

    retry = load(sys.argv[1])
    role = load(sys.argv[2])

    delayed_count = retry.get('delayed_count')
    same_round_direct_full_connect_count = role.get('same_round_direct_full_connect_count')
    same_round_request_peers_count = role.get('same_round_request_peers_count')

    singleton_reason_established = (
        delayed_count == 1
        and same_round_direct_full_connect_count == 1
        and same_round_request_peers_count >= 3
    )

    result = (
        'long_gap_many_round_path_is_singleton_because_same_fanout_round_has_only_one_full_connect_promotion_member'
        if singleton_reason_established
        else 'long_gap_singleton_reason_not_fully_established'
    )

    print(json.dumps({
        'delayed_count': delayed_count,
        'same_round_direct_full_connect_count': same_round_direct_full_connect_count,
        'same_round_request_peers_count': same_round_request_peers_count,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
