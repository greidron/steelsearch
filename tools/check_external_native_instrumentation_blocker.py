#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def load(path):
    return json.loads(Path(path).read_text())

def parse_keyvalish_json_or_lines(path):
    text = Path(path).read_text()
    try:
        return json.loads(text)
    except Exception:
        data = {}
        for line in text.splitlines():
            line = line.strip()
            if '=' in line:
                k, v = line.split('=', 1)
                data[k.strip()] = v.strip()
        return data

def main():
    if len(sys.argv) != 4:
        print('usage: check_external_native_instrumentation_blocker.py PREPARE_PHASE_JSON NEXT_BRANCH_JSON NATIVE_SELECTOR_STOP_JSON')
        return 2
    prepare = load(sys.argv[1])
    next_branch = load(sys.argv[2])
    native_stop = parse_keyvalish_json_or_lines(sys.argv[3])
    result = 'external_native_instrumentation_blocker_not_yet_fixed'
    if (
        prepare.get('prepare_ready_gate') is False
        and next_branch.get('checker_result') == 'next_productive_branch_is_existing_java_inbound_response_delivery_read_starvation_branch_not_actual_run_backlog'
        and native_stop.get('checker_result') == 'selector_boundary_reaches_native_poll_epoll_symbols_and_current_session_lacks_dynamic_visibility_so_this_branch_is_a_practical_stop_point'
    ):
        result = 'external_native_instrumentation_is_the_current_blocker_and_actual_run_backlog_remains_blocked'
    print(json.dumps({
        'prepare_ready_gate': prepare.get('prepare_ready_gate'),
        'prepare_ready_node_count': prepare.get('prepare_ready_node_count'),
        'next_branch_result': next_branch.get('checker_result'),
        'native_selector_stop_result': native_stop.get('checker_result'),
        'checker_result': result,
    }, indent=2))

if __name__ == '__main__':
    raise SystemExit(main())
