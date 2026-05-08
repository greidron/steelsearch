#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def load(path):
    return json.loads(Path(path).read_text())

def parse_keyvalish(path):
    text = Path(path).read_text()
    data = {}
    for line in text.splitlines():
        line = line.strip()
        if '=' in line and not line.startswith('{'):
            k, v = line.split('=', 1)
            data[k.strip()] = v.strip()
    return data

def main():
    if len(sys.argv) != 3:
        print('usage: check_broader_backlog_after_read_starvation_stop.py NEXT_BRANCH_JSON NATIVE_SELECTOR_STOP_JSON')
        return 2
    next_branch = load(sys.argv[1])
    native_stop = parse_keyvalish(sys.argv[2])
    result = 'broader_backlog_branch_unclear'
    if (
        next_branch.get('checker_result') == 'next_productive_branch_is_existing_java_inbound_response_delivery_read_starvation_branch_not_actual_run_backlog'
        and native_stop.get('checker_result') == 'selector_boundary_reaches_native_poll_epoll_symbols_and_current_session_lacks_dynamic_visibility_so_this_branch_is_a_practical_stop_point'
    ):
        result = 'current_session_should_record_read_starvation_as_blocking_backlog_root_pending_external_native_instrumentation'
    print(json.dumps({
        'next_branch_result': next_branch.get('checker_result'),
        'prepare_ready_gate': next_branch.get('prepare_ready_gate'),
        'native_selector_stop_result': native_stop.get('checker_result'),
        'checker_result': result,
    }, indent=2))

if __name__ == '__main__':
    raise SystemExit(main())
