#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_stronger_stop_blocks_actual_run_family.py <stronger-blocked-json> <actual-run-family-json>')
        return 2

    blocked = load(sys.argv[1])
    family = load(sys.argv[2])

    result = {
        'blocked_result': blocked.get('checker_result'),
        'available_new_repo_external_planes': blocked.get('available_new_repo_external_planes', []),
        'prepare_ready_gate': blocked.get('prepare_ready_gate'),
        'family_result': family.get('checker_result'),
    }

    if (
        blocked.get('checker_result')
        == 'stronger_low_intrusion_proof_still_requires_preserving_blocked_practical_stop_until_new_repo_external_capability_or_relief_candidate_appears'
        and family.get('checker_result')
        == 'next_productive_branch_must_be_root_blocker_relief_candidate_since_no_independent_non_actual_run_backlog_branch_remains'
    ):
        result['checker_result'] = (
            'stronger_read_starvation_practical_stop_still_blocks_the_entire_broader_actual_run_family'
        )
    else:
        result['checker_result'] = 'stronger_stop_to_actual_run_family_connection_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
