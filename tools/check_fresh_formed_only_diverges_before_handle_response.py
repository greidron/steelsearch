#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def old_followups(captures):
    count = 0
    for c in captures:
        ff = c.get('first_frame') or {}
        fu = c.get('follow_up_frame') or {}
        if ff.get('action_hint') == 'internal:tcp/handshake' and fu.get('action_hint') == 'internal:transport/handshake':
            count += 1
    return count


def main():
    if len(sys.argv) != 5:
        raise SystemExit('usage: check_fresh_formed_only_diverges_before_handle_response.py HANDSHAKER_SRC TCPTRANSPORT_SRC OLD_CAPTURE CURRENT_STDOUT')
    handshaker = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
    tcptransport = Path(sys.argv[2]).read_text(encoding='utf-8', errors='replace')
    old_capture = json.loads(Path(sys.argv[3]).read_text(encoding='utf-8'))
    stdout = Path(sys.argv[4]).read_text(encoding='utf-8', errors='replace')
    result = 'inconclusive'
    old_follow_up_count = old_followups(old_capture)
    response_read = stdout.count('steelsearch_transport_handshaker_stage=response_read')
    handle_response = stdout.count('steelsearch_transport_handshaker_stage=handle_response')
    onresponse = stdout.count('steelsearch_tcp_open_stage=execute_handshake_listener_onResponse')
    onfailure = stdout.count('steelsearch_tcp_open_stage=execute_handshake_listener_onFailure')
    if (
        'listener.onResponse' in handshaker
        and 'executeHandshake(' in tcptransport
        and old_follow_up_count > 0
        and response_read == 0
        and handle_response == 0
        and onresponse == 0
        and onfailure > 0
    ):
        result = 'fresh_formed_only_regression_diverges_before_TransportHandshaker_handleResponse_and_collapses_into_timeout_onFailure_path'
    print(json.dumps({
        'source_handshaker_has_listener_onResponse': 'listener.onResponse' in handshaker,
        'source_tcptransport_has_executeHandshake': 'executeHandshake(' in tcptransport,
        'old_follow_up_count': old_follow_up_count,
        'current_response_read': response_read,
        'current_handle_response': handle_response,
        'current_execute_handshake_listener_onResponse': onresponse,
        'current_execute_handshake_listener_onFailure': onfailure,
        'checker_result': result,
    }, indent=2))


if __name__ == '__main__':
    main()
