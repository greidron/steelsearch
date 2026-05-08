#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_resume_unavailable_state_should_be_preserved.py <resume-unavailable-json> <top-level-blocked-json>')
        return 2

    resume = load(sys.argv[1])
    top = load(sys.argv[2])

    result = {
        'resume_unavailable_result': resume.get('checker_result'),
        'top_level_blocked_result': top.get('checker_result'),
    }

    if (
        resume.get('checker_result')
        == 'blocked_actual_run_family_cannot_be_resumed_because_no_new_capability_or_relief_candidate_is_currently_available'
        and top.get('checker_result')
        == 'current_top_level_backlog_consists_only_of_the_blocked_actual_run_family_until_new_capability_or_relief_candidate_appears'
    ):
        result['checker_result'] = 'resume_unavailable_state_should_be_preserved_until_new_capability_or_relief_candidate_appears'
    else:
        result['checker_result'] = 'resume_unavailable_state_preservation_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
