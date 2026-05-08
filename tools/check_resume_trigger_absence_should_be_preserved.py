#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_resume_trigger_absence_should_be_preserved.py <resume-state-preserved-json> <current-turn-trigger-json>')
        return 2

    preserved = load(sys.argv[1])
    current = load(sys.argv[2])

    result = {
        'resume_state_preserved_result': preserved.get('checker_result'),
        'current_turn_trigger_result': current.get('checker_result'),
    }

    if (
        preserved.get('checker_result')
        == 'resume_unavailable_state_should_be_preserved_until_new_capability_or_relief_candidate_appears'
        and current.get('checker_result')
        == 'resume_trigger_is_still_absent_in_current_turn'
    ):
        result['checker_result'] = 'resume_trigger_absence_should_continue_to_be_preserved'
    else:
        result['checker_result'] = 'resume_trigger_absence_preservation_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
