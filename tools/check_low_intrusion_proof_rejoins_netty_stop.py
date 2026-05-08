#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    if len(sys.argv) != 4:
        print(
            'usage: check_low_intrusion_proof_rejoins_netty_stop.py <low-intrusion-proof-json> <netty-stop-json> <prepare-phase-json>'
        )
        return 2

    proof = load(sys.argv[1])
    netty_stop = load(sys.argv[2])
    prepare = load(sys.argv[3])

    result = {
        'low_intrusion_result': proof.get('checker_result'),
        'socket_read0_hits': proof.get('socket_read0_hits'),
        'handshake_response_count': proof.get('handshake_response_count'),
        'response_read': proof.get('response_read'),
        'handle_response': proof.get('handle_response'),
        'netty_channel_read': proof.get('netty_channel_read'),
        'netty_stop_result': netty_stop.get('checker_result'),
        'prepare_ready_gate': prepare.get('prepare_ready_gate'),
        'prepare_ready_node_count': prepare.get('prepare_ready_node_count'),
        'prepare_ready_error': prepare.get('prepare_ready_error'),
    }

    if (
        proof.get('checker_result')
        == 'low_intrusion_uprobe_plus_transport_capture_same_run_shows_socket_read0_hits_match_exact_23byte_handshake_response_frames_while_java_response_markers_remain_zero'
        and netty_stop.get('checker_result')
        == 'netty_pipeline_dispatch_javap_does_not_narrow_beyond_same_thread_fireChannelRead_or_async_executor_split_so_current_session_best_boundary_is_repo_external_netty_internal_handoff_practical_stop'
        and prepare.get('prepare_ready_gate') is False
    ):
        result['checker_result'] = (
            'low_intrusion_same_run_read0_proof_rejoins_existing_repo_external_netty_handoff_practical_stop_and_preserves_read_starvation_root_blocker'
        )
    else:
        result['checker_result'] = 'low_intrusion_proof_to_netty_stop_connection_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
