#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_singleton_promotion_member_remove_branch.py <full_connect_path.json> <failure_branch.json>')

    full_connect = load(sys.argv[1])
    failure_branch = load(sys.argv[2])

    singleton_promotion_member = full_connect.get('result') == 'exception_socket_is_unique_full_connect_promotion_member_inside_peerfinder_round'
    singleton_remove_branch_member = failure_branch.get('result') == 'exception_member_is_only_round_member_on_connecting_peer_failure_remove_branch'

    result = (
        'singleton_full_connect_promotion_member_is_same_member_that_takes_remove_branch'
        if singleton_promotion_member and singleton_remove_branch_member
        else 'singleton_promotion_remove_branch_mapping_not_fully_established'
    )

    print(json.dumps({
        'singleton_promotion_member': singleton_promotion_member,
        'singleton_remove_branch_member': singleton_remove_branch_member,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
