#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def count(pattern, text):
    return len(re.findall(pattern, text))


def main():
    if len(sys.argv) != 4:
        print('usage: check_transport_handshake_promotion_gate.py TCPTRANSPORT_JAVA TRANSPORTHANDSHAKER_JAVA STDOUT_LOG', file=sys.stderr)
        return 2

    tcp_path = Path(sys.argv[1])
    hand_path = Path(sys.argv[2])
    stdout_path = Path(sys.argv[3])

    tcp_text = tcp_path.read_text()
    hand_text = hand_path.read_text()
    out = stdout_path.read_text()

    source_has_execute_handshake_listener_onresponse_path = 'listener.onResponse(nodeChannels);' in tcp_text and 'executeHandshake(node, handshakeChannel, connectionProfile, ActionListener.wrap(version -> {' in tcp_text
    source_has_handshake_listener_onresponse = 'listener.onResponse(version);' in hand_text and 'handleResponse(HandshakeResponse response)' in hand_text

    response_read = count(r'steelsearch_transport_handshaker_stage=response_read', out)
    handle_response = count(r'steelsearch_transport_handshaker_stage=handle_response', out)
    execute_onresponse = count(r'steelsearch_tcp_open_stage=execute_handshake_listener_onResponse', out)
    execute_onfailure = count(r'steelsearch_tcp_open_stage=execute_handshake_listener_onFailure', out)

    print(f'source_tcptransport_has_execute_handshake_onresponse_path={source_has_execute_handshake_listener_onresponse_path}')
    print(f'source_transportunshaker_has_listener_onresponse={source_has_handshake_listener_onresponse}')
    print(f'actual_response_read={response_read}')
    print(f'actual_handle_response={handle_response}')
    print(f'actual_execute_handshake_listener_onResponse={execute_onresponse}')
    print(f'actual_execute_handshake_listener_onFailure={execute_onfailure}')

    if (
        source_has_execute_handshake_listener_onresponse_path
        and source_has_handshake_listener_onresponse
        and response_read == 0
        and handle_response == 0
        and execute_onresponse == 0
        and execute_onfailure > 0
    ):
        result = 'current_promotion_gate_is_transport_handshaker_handleResponse_to_executeHandshake_listener_onResponse_chain_and_current_runtime_never_opens_it'
    else:
        result = 'inconclusive'
    print(f'checker_result={result}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
