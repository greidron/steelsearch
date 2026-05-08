#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        print(json.dumps({'error': 'usage: check_mixed_open_connection_like_lifecycle.py <open_vs_reuse_contract.json> <mixed_no_reuse.json> <mixed_lifecycle_matrix.json>'}))
        return 1
    contract = load(sys.argv[1])
    no_reuse = load(sys.argv[2])
    lifecycle = load(sys.argv[3])

    source_contract_present = bool(
        contract.get('open_connection_calls_internal_open_connection')
        and contract.get('connect_to_node_registers_connected_nodes')
        and contract.get('get_connection_uses_connected_nodes')
        and contract.get('node_connected_depends_on_connected_nodes')
    )
    no_reusable_channel = bool(no_reuse.get('all_coordinator_actions_arrive_as_connection_first_frame'))
    one_shot_lifecycle = lifecycle.get('result') == 'coordinator_sockets_are_uniform_one_shot_sub_threshold_remote_eof_lifecycle'

    if source_contract_present and no_reusable_channel and one_shot_lifecycle:
        result = 'mixed_runtime_looks_like_repeated_open_connection_without_connected_nodes_reuse'
    elif not source_contract_present:
        result = 'source_open_vs_reuse_contract_not_detected'
    else:
        result = 'open_connection_like_lifecycle_not_isolated'

    print(json.dumps({
        'source_open_vs_reuse_contract_present': source_contract_present,
        'mixed_no_reusable_channel': no_reusable_channel,
        'mixed_one_shot_lifecycle': one_shot_lifecycle,
        'result': result,
    }))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
