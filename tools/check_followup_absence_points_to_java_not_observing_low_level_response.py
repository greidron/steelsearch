#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_followup_absence_points_to_java_not_observing_low_level_response.py <opensearch-stdout.log> <report.json>', file=sys.stderr)
        return 2

    stdout = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
    report = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    captures = report.get('steelsearch_transport_capture') or []
    actions = {(entry.get('first_frame') or {}).get('action_hint') for entry in captures}

    before_send = stdout.count('steelsearch_transport_handshaker_stage=before_send_request')
    response_read = stdout.count('steelsearch_transport_handshaker_stage=response_read')
    on_response = stdout.count('steelsearch_tcp_open_stage=execute_handshake_listener_onResponse')
    send_tcp = stdout.count('steelsearch_native_outbound_stage=send_request_meta requestId=')
    send_transport = stdout.count('action=internal:transport/handshake')
    send_tcp_action = stdout.count('action=internal:tcp/handshake')

    print(f'before_send_request={before_send}')
    print(f'response_read={response_read}')
    print(f'execute_handshake_listener_onResponse={on_response}')
    print(f'send_request_meta_total={send_tcp}')
    print(f'send_request_meta_tcp_handshake={send_tcp_action}')
    print(f'send_request_meta_transport_handshake={send_transport}')
    print(f'capture_actions={sorted(actions, key=lambda x: str(x))}')

    if (
        before_send > 0
        and response_read == 0
        and on_response == 0
        and send_tcp_action > 0
        and send_transport == 0
        and actions <= {None, 'internal:tcp/handshake'}
    ):
        print('result=followup_absence_points_to_java_not_observing_low_level_tcp_handshake_response_so_peer_never_sends_followup')
        return 0

    print('result=followup_absence_cause_not_yet_decisive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
