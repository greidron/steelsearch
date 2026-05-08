#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text())


def main():
    if len(sys.argv) != 3:
        print('usage: check_netty_internal_stop_matches_read_starvation_block.py <netty-stop-json> <blocked-subtree-json>')
        return 2

    netty = load(sys.argv[1])
    blocked = load(sys.argv[2])

    result = {
        'netty_stop_path': sys.argv[1],
        'netty_stop_result': netty.get('checker_result'),
        'blocked_path': sys.argv[2],
        'blocked_result': blocked.get('checker_result'),
    }

    if (
        netty.get('checker_result') == 'netty_pipeline_dispatch_javap_does_not_narrow_beyond_same_thread_fireChannelRead_or_async_executor_split_so_current_session_best_boundary_is_repo_external_netty_internal_handoff_practical_stop'
        and blocked.get('checker_result') == 'read_starvation_subtree_should_remain_blocked_until_materially_different_capability_or_new_relief_candidate_appears'
    ):
        result['checker_result'] = 'repo_external_netty_internal_handoff_practical_stop_rejoins_existing_read_starvation_root_blocked_state'
    else:
        result['checker_result'] = 'undetermined'

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    raise SystemExit(main())
