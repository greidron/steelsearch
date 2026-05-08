#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path


TRANSPORT_READ_RE = re.compile(r"^\d+\s+\S+\s+read\(191<TCPv6:.*\)\s+=\s+29\b")


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({'error': 'usage: check_transport_worker_payload_read_vs_java_markers.py <work-dir>'}, indent=2))
        return 2

    work_dir = Path(sys.argv[1])
    strace_path = work_dir / 'opensearch' / 'late-strace.log'
    stdout_path = work_dir / 'opensearch' / 'stdout.log'

    strace_text = strace_path.read_text(encoding='utf-8', errors='replace')
    stdout_text = stdout_path.read_text(encoding='utf-8', errors='replace')

    transport_payload_reads = sum(1 for line in strace_text.splitlines() if TRANSPORT_READ_RE.match(line))
    marker_counts = Counter({
        'response_read': stdout_text.count('response_read'),
        'handle_response': stdout_text.count('handle_response'),
        'execute_handshake_listener_onResponse': stdout_text.count('execute_handshake_listener_onResponse'),
        'execute_handshake_listener_onFailure': stdout_text.count('execute_handshake_listener_onFailure'),
        'netty_channel_read': stdout_text.count('netty_channel_read'),
        'channelRead': stdout_text.count('channelRead'),
        'open_response': stdout_text.count('open_response'),
    })

    result = {
        'transport_worker_tcp_payload_read_29b_count': transport_payload_reads,
        'java_marker_counts': dict(marker_counts),
    }

    if (
        transport_payload_reads > 0
        and marker_counts['response_read'] == 0
        and marker_counts['handle_response'] == 0
        and marker_counts['execute_handshake_listener_onResponse'] == 0
        and marker_counts['netty_channel_read'] == 0
        and marker_counts['channelRead'] == 0
        and marker_counts['execute_handshake_listener_onFailure'] > 0
    ):
        result['checker_result'] = 'same_run_transport_worker_payload_reads_exist_but_java_response_markers_stay_zero_so_boundary_is_above_socket_read_and_below_netty_response_dispatch'
    else:
        result['checker_result'] = 'same_run_transport_worker_payload_read_vs_java_marker_boundary_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
