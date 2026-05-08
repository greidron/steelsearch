#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_low_intrusion_uprobe_vs_capture_identity.py <work-dir>')
        return 2

    work_dir = Path(sys.argv[1])
    summary = json.loads((Path(f"{work_dir}-summary.json")).read_text(encoding='utf-8'))
    capture = json.loads((work_dir / 'steelsearch' / 'data' / 'transport-seed-capture.json').read_text(encoding='utf-8'))
    stdout_text = (work_dir / 'opensearch' / 'stdout.log').read_text(encoding='utf-8', errors='replace')

    socket_hits = summary.get('perf_counts', {}).get('probe_libnio:ss_socket_read0', 0)
    unix_hits = summary.get('perf_counts', {}).get('probe_libnio:ss_unix_read0', 0)
    window_start = summary.get('perf_window_start_ms')
    window_end = summary.get('perf_window_end_ms')

    handshake_responses = []
    for row in capture:
        response = row.get('response_frame')
        if not response:
            continue
        sent_at = row.get('response_frame_sent_at_ms')
        if (
            window_start is not None
            and window_end is not None
            and isinstance(sent_at, int)
            and not (window_start <= sent_at <= window_end)
        ):
            continue
        if response.get('is_handshake') and response.get('is_response'):
            handshake_responses.append(
                {
                    'peer_addr': row.get('peer_addr'),
                    'request_id': response.get('request_id'),
                    'message_length': response.get('message_length'),
                    'body_len': response.get('body_len'),
                    'body_prefix_hex': response.get('body_prefix_hex'),
                }
            )

    result = {
        'socket_read0_hits': socket_hits,
        'unix_read0_hits': unix_hits,
        'perf_window_start_ms': window_start,
        'perf_window_end_ms': window_end,
        'handshake_response_count': len(handshake_responses),
        'handshake_response_peers': sorted({row['peer_addr'] for row in handshake_responses}),
        'response_read': stdout_text.count('response_read'),
        'handle_response': stdout_text.count('handle_response'),
        'execute_handshake_listener_onResponse': stdout_text.count('execute_handshake_listener_onResponse'),
        'execute_handshake_listener_onFailure': stdout_text.count('execute_handshake_listener_onFailure'),
        'netty_channel_read': stdout_text.count('netty_channel_read'),
        'channelRead': stdout_text.count('channelRead'),
    }

    if (
        socket_hits > 0
        and socket_hits == len(handshake_responses)
        and all(row['message_length'] == 23 and row['body_len'] == 23 for row in handshake_responses)
        and result['response_read'] == 0
        and result['handle_response'] == 0
        and result['execute_handshake_listener_onResponse'] == 0
        and result['netty_channel_read'] == 0
        and result['channelRead'] == 0
        and result['execute_handshake_listener_onFailure'] > 0
    ):
        result['checker_result'] = (
            'low_intrusion_uprobe_plus_transport_capture_same_run_shows_socket_read0_hits_match_exact_23byte_handshake_response_frames_while_java_response_markers_remain_zero'
        )
    else:
        result['checker_result'] = 'low_intrusion_uprobe_vs_capture_identity_correlation_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
