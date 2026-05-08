#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_no_actionable_progress_remaining_in_current_env.py <top-level-blocked-json> <trigger-absence-preserved-json>')
        return 2

    top = load(sys.argv[1])
    trigger = load(sys.argv[2])

    result = {
        'top_level_blocked_result': top.get('checker_result'),
        'trigger_absence_preserved_result': trigger.get('checker_result'),
    }

    if (
        top.get('checker_result')
        == 'current_top_level_backlog_consists_only_of_the_blocked_actual_run_family_until_new_capability_or_relief_candidate_appears'
        and trigger.get('checker_result')
        == 'resume_trigger_absence_should_continue_to_be_preserved'
    ):
        result['checker_result'] = 'no_actionable_progress_remaining_in_current_environment_until_external_change'
    else:
        result['checker_result'] = 'actionability_status_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
