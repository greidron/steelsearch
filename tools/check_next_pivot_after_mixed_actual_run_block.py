#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path_str):
    path = Path(path_str)
    return path, json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    blocked_path, blocked = load(sys.argv[1])
    tasks_path = Path(sys.argv[2])
    tasks_text = tasks_path.read_text(encoding='utf-8')
    has_rolling_restart_branch = 'Java-driven rolling restart actual run evidence 수집' in tasks_text
    has_bulk_replay_leaf = 'bulk replay actual run' in tasks_text
    result = {
        'blocked_path': str(blocked_path),
        'blocked_result': blocked.get('checker_result'),
        'has_rolling_restart_branch': has_rolling_restart_branch,
        'has_bulk_replay_leaf': has_bulk_replay_leaf,
    }
    if (
        blocked.get('checker_result') == 'read_starvation_root_blocker_is_what_keeps_broader_mixed_actual_run_backlog_blocked'
        and has_rolling_restart_branch
        and has_bulk_replay_leaf
    ):
        result['checker_result'] = 'next_productive_step_is_not_another_actual_run_subtree_but_preserving_actual_run_family_as_blocked_under_read_starvation_root_blocker'
    else:
        result['checker_result'] = 'next_pivot_after_mixed_actual_run_block_remains_unclear'
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
