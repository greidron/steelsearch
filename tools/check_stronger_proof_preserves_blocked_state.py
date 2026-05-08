#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_stronger_proof_preserves_blocked_state.py <rejoin-json> <capability-frontier-json>')
        return 2

    rejoin = load(sys.argv[1])
    frontier = load(sys.argv[2])

    result = {
        'rejoin_result': rejoin.get('checker_result'),
        'socket_read0_hits': rejoin.get('socket_read0_hits'),
        'handshake_response_count': rejoin.get('handshake_response_count'),
        'prepare_ready_gate': rejoin.get('prepare_ready_gate'),
        'capability_frontier_result': frontier.get('checker_result'),
        'available_new_repo_external_planes': frontier.get('available_new_repo_external_planes', []),
    }

    if (
        rejoin.get('checker_result')
        == 'low_intrusion_same_run_read0_proof_rejoins_existing_repo_external_netty_handoff_practical_stop_and_preserves_read_starvation_root_blocker'
        and frontier.get('checker_result')
        == 'no_additional_repo_external_visibility_plane_binary_is_currently_available_beyond_already_used_capabilities'
        and rejoin.get('prepare_ready_gate') is False
    ):
        result['checker_result'] = (
            'stronger_low_intrusion_proof_still_requires_preserving_blocked_practical_stop_until_new_repo_external_capability_or_relief_candidate_appears'
        )
    else:
        result['checker_result'] = 'stronger_proof_blocked_state_preservation_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
