#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def load(path_str):
    path = Path(path_str)
    return path, json.loads(path.read_text(encoding='utf-8'))

def main() -> int:
    root_path, root = load(sys.argv[1])
    prepare_path, prepare = load(sys.argv[2])
    result = {
        'root_path': str(root_path),
        'root_result': root.get('checker_result'),
        'prepare_path': str(prepare_path),
        'prepare_ready_gate': prepare.get('prepare_ready_gate'),
        'prepare_ready_node_count': prepare.get('prepare_ready_node_count'),
        'prepare_ready_error': prepare.get('prepare_ready_error'),
    }
    if (
        root.get('checker_result') == 'non_intrusive_jit_stop_is_not_a_new_branch_it_rejoins_existing_java_inbound_response_delivery_read_starvation_root_blocker'
        and prepare.get('prepare_ready_gate') is False
        and prepare.get('prepare_ready_node_count') == 0
    ):
        result['checker_result'] = 'read_starvation_root_blocker_is_what_keeps_broader_mixed_actual_run_backlog_blocked'
    else:
        result['checker_result'] = 'connection_between_read_starvation_root_and_actual_run_block_remains_incomplete'
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
