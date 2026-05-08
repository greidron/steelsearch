#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text())


def main():
    if len(sys.argv) != 3:
        print('usage: check_netty_stop_preserves_blocked_state.py <netty-rejoin-json> <blocked-subtree-json>')
        return 2

    netty = load(sys.argv[1])
    blocked = load(sys.argv[2])

    result = {
        'netty_rejoin_path': sys.argv[1],
        'netty_rejoin_result': netty.get('checker_result'),
        'blocked_path': sys.argv[2],
        'blocked_result': blocked.get('checker_result'),
    }

    if (
        netty.get('checker_result') == 'repo_external_netty_internal_handoff_practical_stop_rejoins_existing_read_starvation_root_blocked_state'
        and blocked.get('checker_result') == 'read_starvation_subtree_should_remain_blocked_until_materially_different_capability_or_new_relief_candidate_appears'
    ):
        result['checker_result'] = 'current_read_starvation_subtree_must_remain_blocked_until_materially_different_netty_jvm_native_capability_or_new_relief_candidate_appears'
    else:
        result['checker_result'] = 'undetermined'

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    raise SystemExit(main())
