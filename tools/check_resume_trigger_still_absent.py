#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_resume_trigger_still_absent.py <resume-unavailable-json> <expanded-frontier-json>')
        return 2

    resume = load(sys.argv[1])
    frontier = load(sys.argv[2])

    result = {
        'resume_unavailable_result': resume.get('checker_result'),
        'available_new_repo_external_planes': frontier.get('available_new_repo_external_planes', []),
        'capability_frontier_result': frontier.get('checker_result'),
    }

    if (
        resume.get('checker_result')
        == 'blocked_actual_run_family_cannot_be_resumed_because_no_new_capability_or_relief_candidate_is_currently_available'
        and frontier.get('checker_result')
        == 'no_additional_repo_external_visibility_plane_binary_is_currently_available_beyond_already_used_capabilities'
    ):
        result['checker_result'] = 'resume_trigger_is_still_absent_in_current_turn'
    else:
        result['checker_result'] = 'resume_trigger_status_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
