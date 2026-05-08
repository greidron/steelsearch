#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path_str):
    path = Path(path_str)
    return path, json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    stop_path, stop = load(sys.argv[1])
    next_branch_path, next_branch = load(sys.argv[2])
    result = {
        'stop_path': str(stop_path),
        'stop_result': stop.get('checker_result'),
        'next_branch_path': str(next_branch_path),
        'next_branch_result': next_branch.get('checker_result'),
    }
    if (
        stop.get('checker_result') == 'root_blocker_relief_family_practical_stop_matches_current_session_broader_read_starvation_stop_point'
        and next_branch.get('checker_result') == 'next_productive_branch_must_be_root_blocker_relief_candidate_since_no_independent_non_actual_run_backlog_branch_remains'
    ):
        result['checker_result'] = 'read_starvation_subtree_should_remain_blocked_until_materially_different_capability_or_new_relief_candidate_appears'
    else:
        result['checker_result'] = 'blocked_state_preservation_decision_remains_unclear'
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
