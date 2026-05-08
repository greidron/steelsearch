#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_singleton_branch_specificity.py <same_round_remote_eof.json> <exception_full_connect_path.json> <exception_failure_branch.json>')

    eof_dist = load(sys.argv[1])
    full_connect = load(sys.argv[2])
    failure_branch = load(sys.argv[3])

    eof_is_round_wide = eof_dist.get('result') == 'all_same_round_members_get_remote_eof_so_exception_is_branch_specific_not_eof_specific'
    singleton_is_unique_full_connect_member = (
        full_connect.get('result') == 'exception_socket_is_unique_full_connect_promotion_member_inside_peerfinder_round'
    )
    singleton_is_unique_remove_branch_member = (
        failure_branch.get('result') == 'exception_member_is_only_round_member_on_connecting_peer_failure_remove_branch'
    )

    result = (
        'singleton_member_is_branch_specific_full_connect_remove_member_while_remote_eof_is_round_wide'
        if eof_is_round_wide and singleton_is_unique_full_connect_member and singleton_is_unique_remove_branch_member
        else 'singleton_branch_specificity_not_fully_established'
    )

    print(json.dumps({
        'eof_is_round_wide': eof_is_round_wide,
        'singleton_is_unique_full_connect_member': singleton_is_unique_full_connect_member,
        'singleton_is_unique_remove_branch_member': singleton_is_unique_remove_branch_member,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
