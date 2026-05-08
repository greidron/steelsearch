#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_no_nonblocked_leaf_outside_actual_run_family.py <family-blocked-until-new-capability-json> <next-branch-json>')
        return 2

    blocked = load(sys.argv[1])
    next_branch = load(sys.argv[2])

    result = {
        'family_blocked_until_new_capability_result': blocked.get('checker_result'),
        'next_branch_result': next_branch.get('checker_result'),
    }

    if (
        blocked.get('checker_result')
        == 'broader_actual_run_family_should_remain_blocked_until_materially_different_capability_or_genuinely_new_relief_candidate_appears'
        and next_branch.get('checker_result')
        == 'next_productive_branch_must_be_root_blocker_relief_candidate_since_no_independent_non_actual_run_backlog_branch_remains'
    ):
        result['checker_result'] = 'no_immediately_actionable_non_blocked_leaf_remains_outside_the_blocked_actual_run_family'
    else:
        result['checker_result'] = 'top_level_backlog_recheck_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
