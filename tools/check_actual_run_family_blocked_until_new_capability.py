#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_actual_run_family_blocked_until_new_capability.py <family-blocked-json> <capability-frontier-json>')
        return 2

    blocked = load(sys.argv[1])
    frontier = load(sys.argv[2])

    result = {
        'family_blocked_result': blocked.get('checker_result'),
        'available_new_repo_external_planes': frontier.get('available_new_repo_external_planes', []),
        'capability_frontier_result': frontier.get('checker_result'),
    }

    if (
        blocked.get('checker_result')
        == 'stronger_read_starvation_practical_stop_still_blocks_the_entire_broader_actual_run_family'
        and frontier.get('checker_result')
        == 'no_additional_repo_external_visibility_plane_binary_is_currently_available_beyond_already_used_capabilities'
    ):
        result['checker_result'] = (
            'broader_actual_run_family_should_remain_blocked_until_materially_different_capability_or_genuinely_new_relief_candidate_appears'
        )
    else:
        result['checker_result'] = 'actual_run_family_blocked_state_preservation_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
