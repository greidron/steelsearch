#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path_str):
    path = Path(path_str)
    return path, json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    relief_path, relief = load(sys.argv[1])
    blocked_path, blocked = load(sys.argv[2])
    next_branch_path, next_branch = load(sys.argv[3])
    result = {
        'relief_path': str(relief_path),
        'relief_result': relief.get('checker_result'),
        'blocked_path': str(blocked_path),
        'blocked_result': blocked.get('checker_result'),
        'next_branch_path': str(next_branch_path),
        'next_branch_result': next_branch.get('checker_result'),
    }
    if (
        relief.get('checker_result') == 'root_blocker_relief_candidate_family_reached_practical_stop_without_recovering_higher_caller_frames'
        and blocked.get('checker_result') == 'read_starvation_root_blocker_is_what_keeps_broader_mixed_actual_run_backlog_blocked'
        and next_branch.get('checker_result') == 'next_productive_branch_must_be_root_blocker_relief_candidate_since_no_independent_non_actual_run_backlog_branch_remains'
    ):
        result['checker_result'] = 'root_blocker_relief_family_practical_stop_matches_current_session_broader_read_starvation_stop_point'
    else:
        result['checker_result'] = 'root_blocker_relief_family_connection_to_session_stop_point_remains_incomplete'
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
