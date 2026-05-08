#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    if len(sys.argv) != 4:
        print('usage: check_same_run_uprobe_vs_tuple_branch.py <uprobe-summary-json> <tcpv6-vs-capture-json> <payload-vs-markers-json>')
        return 2

    uprobe = load(sys.argv[1])
    tcpv6 = load(sys.argv[2])
    markers = load(sys.argv[3])

    socket_hits = uprobe.get('perf_counts', {}).get('probe_libnio:ss_socket_read0', 0)
    unix_hits = uprobe.get('perf_counts', {}).get('probe_libnio:ss_unix_read0', 0)
    marker_counts = markers.get('java_marker_counts', {})
    overlap = tcpv6.get('capture_peer_ports_overlap', [])
    selector_tids = tcpv6.get('selector_tuple_tids', [])
    non_selector_tids = tcpv6.get('non_selector_tuple_tids', [])

    result = {
        'socket_read0_hits': socket_hits,
        'unix_read0_hits': unix_hits,
        'capture_peer_ports_overlap': overlap,
        'selector_tuple_tids': selector_tids,
        'non_selector_tuple_tids': non_selector_tids,
        'response_read': marker_counts.get('response_read', 0),
        'handle_response': marker_counts.get('handle_response', 0),
        'netty_channel_read': marker_counts.get('netty_channel_read', 0),
        'execute_handshake_listener_onFailure': marker_counts.get('execute_handshake_listener_onFailure', 0),
    }

    if (
        socket_hits > 0
        and overlap
        and selector_tids
        and not non_selector_tids
        and marker_counts.get('response_read', 0) == 0
        and marker_counts.get('handle_response', 0) == 0
        and marker_counts.get('netty_channel_read', 0) == 0
        and marker_counts.get('execute_handshake_listener_onFailure', 0) > 0
        and unix_hits > socket_hits
    ):
        result['checker_result'] = (
            'same_run_socket_read0_hits_align_with_starvation_same_socket_selector_branch_while_unix_read0_hits_are_dominated_by_broader_background_io'
        )
    else:
        result['checker_result'] = 'same_run_uprobe_vs_tuple_branch_correlation_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
