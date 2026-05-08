#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text())


def main():
    if len(sys.argv) != 3:
        print('usage: check_native_wrapper_read_candidates.py <socket-read0-check.json> <unix-read0-check.json>')
        return 2
    socket = load(sys.argv[1])
    unix = load(sys.argv[2])
    result = {
        'socket_read0_result': socket.get('checker_result'),
        'socket_read0_samples': socket.get('socket_dispatcher_read0_samples'),
        'unix_read0_result': unix.get('checker_result'),
        'unix_read0_samples': unix.get('unix_file_dispatcher_read0_samples'),
    }
    if socket.get('socket_dispatcher_read0_samples') == 0 and unix.get('unix_file_dispatcher_read0_samples') == 0:
        result['checker_result'] = 'direct_native_wrapper_async_profiler_method_candidates_did_not_capture_exact_native_read_boundary'
    else:
        result['checker_result'] = 'native_wrapper_candidate_hit_detected'
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    raise SystemExit(main())
