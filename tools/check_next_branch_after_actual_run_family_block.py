#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def load(path_str):
    path = Path(path_str)
    return path, json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    blocked_path, blocked = load(sys.argv[1])
    tasks_path = Path(sys.argv[2])
    top_level_unchecked = []
    for line in tasks_path.read_text(encoding='utf-8').splitlines():
        if line.startswith('      - [ ] '):
            top_level_unchecked.append(line.strip())
    all_actual_run = all('actual run evidence 수집' in line for line in top_level_unchecked) if top_level_unchecked else False
    result = {
        'blocked_path': str(blocked_path),
        'blocked_result': blocked.get('checker_result'),
        'top_level_unchecked': top_level_unchecked,
        'all_top_level_unchecked_are_actual_run_families': all_actual_run,
    }
    if (
        blocked.get('checker_result') == 'next_productive_step_is_not_another_actual_run_subtree_but_preserving_actual_run_family_as_blocked_under_read_starvation_root_blocker'
        and all_actual_run
        and len(top_level_unchecked) > 0
    ):
        result['checker_result'] = 'next_productive_branch_must_be_root_blocker_relief_candidate_since_no_independent_non_actual_run_backlog_branch_remains'
    else:
        result['checker_result'] = 'next_branch_after_actual_run_family_block_remains_unclear'
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
