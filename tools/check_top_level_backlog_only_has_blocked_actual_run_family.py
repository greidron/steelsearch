#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_top_level_backlog_only_has_blocked_actual_run_family.py <no-nonblocked-leaf-json> <family-blocked-until-new-capability-json>')
        return 2

    no_leaf = load(sys.argv[1])
    blocked = load(sys.argv[2])

    result = {
        'no_nonblocked_leaf_result': no_leaf.get('checker_result'),
        'family_blocked_until_new_capability_result': blocked.get('checker_result'),
    }

    if (
        no_leaf.get('checker_result')
        == 'no_immediately_actionable_non_blocked_leaf_remains_outside_the_blocked_actual_run_family'
        and blocked.get('checker_result')
        == 'broader_actual_run_family_should_remain_blocked_until_materially_different_capability_or_genuinely_new_relief_candidate_appears'
    ):
        result['checker_result'] = 'current_top_level_backlog_consists_only_of_the_blocked_actual_run_family_until_new_capability_or_relief_candidate_appears'
    else:
        result['checker_result'] = 'top_level_blocked_backlog_preservation_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
