#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_singleton_remove_branch_remote_eof_trigger.py <failure_branch.json> <exception_timeline.json>')

    branch = load(sys.argv[1])
    timeline = load(sys.argv[2])

    remove_branch_established = branch.get('result') == 'exception_member_is_only_round_member_on_connecting_peer_failure_remove_branch'
    entries = timeline.get('timeline') or []
    remote_eof_singleton = (
        len(entries) == 1
        and entries[0].get('first_action') == 'internal:transport/handshake'
        and entries[0].get('first_post_response_event') == 'remote_eof'
        and entries[0].get('connection_end') == 'remote_eof'
    )

    result = (
        'singleton_promotion_member_is_sent_to_remove_branch_by_transport_handshake_remote_eof'
        if remove_branch_established and remote_eof_singleton
        else 'singleton_remove_branch_remote_eof_trigger_not_fully_established'
    )

    print(json.dumps({
        'remove_branch_established': remove_branch_established,
        'remote_eof_singleton': remote_eof_singleton,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
