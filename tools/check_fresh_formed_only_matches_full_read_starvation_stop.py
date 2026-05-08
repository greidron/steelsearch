#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def parse_delayed_checker(path: str):
    data = {}
    for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            data[k.strip()] = v.strip()
    return data


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_fresh_formed_only_matches_full_read_starvation_stop.py STARVATION_CHECKER_TXT CURRENT_STDOUT')
    starvation = parse_delayed_checker(sys.argv[1])
    stdout = Path(sys.argv[2]).read_text(encoding='utf-8', errors='replace')
    current = {
        'response_read': stdout.count('steelsearch_transport_handshaker_stage=response_read'),
        'handle_response': stdout.count('steelsearch_transport_handshaker_stage=handle_response'),
        'execute_handshake_listener_onFailure': stdout.count('steelsearch_tcp_open_stage=execute_handshake_listener_onFailure'),
        'channel_read': stdout.count('steelsearch_netty4_message_channel_stage=channel_read'),
        'handshake_timeout': stdout.count('handshake_timeout[1s]'),
        'explicit_local_close': stdout.count('hint=explicitLocalClose'),
    }
    result = 'inconclusive'
    if (
        starvation.get('checker_result') == 'delayed_timeout_same_socket_still_never_reaches_channelRead'
        and current['response_read'] == 0
        and current['handle_response'] == 0
        and current['execute_handshake_listener_onFailure'] > 0
        and current['handshake_timeout'] > 0
        and current['explicit_local_close'] > 0
    ):
        result = 'fresh_formed_only_regression_remaining_unknown_matches_existing_full_opensearch_read_starvation_practical_stop'
    print(json.dumps({
        'starvation_checker_result': starvation.get('checker_result'),
        'current': current,
        'checker_result': result,
    }, indent=2))


if __name__ == '__main__':
    main()
