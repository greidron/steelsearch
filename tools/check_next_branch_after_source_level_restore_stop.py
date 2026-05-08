#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def load(path):
    return json.loads(Path(path).read_text())

def main():
    if len(sys.argv) != 3:
        print('usage: check_next_branch_after_source_level_restore_stop.py PREPARE_PHASE_JSON SOURCE_LEVEL_STOP_JSON')
        return 2
    prepare = load(sys.argv[1])
    stop = load(sys.argv[2])
    result = 'next_productive_branch_unclear'
    if prepare.get('prepare_ready_gate') is False and stop.get('checker_result') == 'source_level_restore_family_matches_existing_full_read_starvation_practical_stop':
        result = 'next_productive_branch_is_existing_java_inbound_response_delivery_read_starvation_branch_not_actual_run_backlog'
    print(json.dumps({
        'prepare_ready_gate': prepare.get('prepare_ready_gate'),
        'prepare_ready_node_count': prepare.get('prepare_ready_node_count'),
        'prepare_ready_error': prepare.get('prepare_ready_error'),
        'source_level_stop_result': stop.get('checker_result'),
        'checker_result': result,
    }, indent=2))

if __name__ == '__main__':
    raise SystemExit(main())
