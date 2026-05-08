#!/usr/bin/env python3
import json
import re
import statistics
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            'usage: check_idle_handshake_close_points_below_explicit_java_transport_timers.py <mixed_artifact.json> <TcpTransport.java> <transport-netty4-dir>',
            file=sys.stderr,
        )
        return 2

    artifact_path = Path(sys.argv[1])
    tcp_transport_path = Path(sys.argv[2])
    netty4_dir = Path(sys.argv[3])

    with artifact_path.open() as f:
        data = json.load(f)
    tcp_transport_text = tcp_transport_path.read_text()

    netty4_text = ''
    for path in netty4_dir.rglob('*.java'):
        netty4_text += path.read_text() + '\n'

    capture = data['steelsearch_transport_capture']
    gaps = [
        item['connection_end_at_ms'] - item['response_frame_sent_at_ms']
        for item in capture
        if (item.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake'
    ]

    source_tcptransport_only_explicit_timeout_is_connect = 'connect_timeout[' in tcp_transport_text and 'channelsConnectedListener::onTimeout' in tcp_transport_text
    source_netty4_has_idle_state_handler = 'IdleStateHandler' in netty4_text
    source_netty4_has_read_or_write_timeout_handler = bool(re.search(r'(ReadTimeoutHandler|WriteTimeoutHandler)', netty4_text))

    result = {
        'idle_handshake_close_gap_ms': {
            'min': min(gaps),
            'median': statistics.median(gaps),
            'max': max(gaps),
        },
        'source_tcptransport_only_explicit_timeout_is_connect': source_tcptransport_only_explicit_timeout_is_connect,
        'source_netty4_has_idle_state_handler': source_netty4_has_idle_state_handler,
        'source_netty4_has_read_or_write_timeout_handler': source_netty4_has_read_or_write_timeout_handler,
        'result': 'idle_handshake_close_points_below_explicit_java_transport_and_explicit_netty_idle_timer_source'
        if max(gaps) < 1000
        and source_tcptransport_only_explicit_timeout_is_connect
        and source_netty4_has_idle_state_handler is False
        and source_netty4_has_read_or_write_timeout_handler is False
        else 'explicit_java_transport_or_netty_idle_timer_source_not_ruled_out',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
