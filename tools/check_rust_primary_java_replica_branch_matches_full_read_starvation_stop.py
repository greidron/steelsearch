#!/usr/bin/env python3
import re
import sys
from pathlib import Path

TIMEOUT_BRANCH_RE = re.compile(
    r"steelsearch_tcp_open_stage=execute_handshake_failure_timeout_branch node=\{127\.0\.0\.1:(\d+)\}"
)
CLOSE_RE = re.compile(
    r"steelsearch_tcp_open_stage=close_and_fail_enter node=\{127\.0\.0\.1:(\d+)\}.*causeMessage=\[\]\[127\.0\.0\.1:\1\] handshake_timeout\[5s\]"
)
CHANNEL_READ_RE = re.compile(
    r"steelsearch_netty4_message_channel_stage=channel_read local=/127\.0\.0\.1:(\d+) remote=/127\.0\.0\.1:(\d+)"
)


def main():
    if len(sys.argv) != 4:
        print(
            'usage: check_rust_primary_java_replica_branch_matches_full_read_starvation_stop.py STARVATION_STDOUT TCPTRANSPORT_JAVA CURRENT_STDOUT',
            file=sys.stderr,
        )
        return 2

    starvation_stdout = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
    tcptransport_java = Path(sys.argv[2]).read_text(encoding='utf-8', errors='replace')
    current_stdout = Path(sys.argv[3]).read_text(encoding='utf-8', errors='replace')

    timeout_ports = {int(m.group(1)) for m in TIMEOUT_BRANCH_RE.finditer(starvation_stdout)}
    close_ports = {int(m.group(1)) for m in CLOSE_RE.finditer(starvation_stdout)}
    read_local_ports = {int(m.group(1)) for m in CHANNEL_READ_RE.finditer(starvation_stdout)}

    same_socket_no_channel_read = bool(timeout_ports) and not (timeout_ports & read_local_ports) and not (close_ports & read_local_ports)
    source_has_execute_handshake_onresponse_path = 'listener.onResponse(nodeChannels);' in tcptransport_java
    current_response_read = len(re.findall(r'steelsearch_transport_handshaker_stage=response_read', current_stdout))
    current_handle_response = len(re.findall(r'steelsearch_transport_handshaker_stage=handle_response', current_stdout))
    current_execute_onresponse = len(re.findall(r'steelsearch_tcp_open_stage=execute_handshake_listener_onResponse', current_stdout))
    current_execute_onfailure = len(re.findall(r'steelsearch_tcp_open_stage=execute_handshake_listener_onFailure', current_stdout))

    print(f'starvation_timeout_ports={len(timeout_ports)}')
    print(f'starvation_close_ports={len(close_ports)}')
    print(f'starvation_read_local_ports={len(read_local_ports)}')
    print(f'starvation_same_socket_no_channel_read={same_socket_no_channel_read}')
    print(f'source_has_execute_handshake_onresponse_path={source_has_execute_handshake_onresponse_path}')
    print(f'current_response_read={current_response_read}')
    print(f'current_handle_response={current_handle_response}')
    print(f'current_execute_handshake_listener_onResponse={current_execute_onresponse}')
    print(f'current_execute_handshake_listener_onFailure={current_execute_onfailure}')

    if (
        same_socket_no_channel_read
        and source_has_execute_handshake_onresponse_path
        and current_response_read == 0
        and current_handle_response == 0
        and current_execute_onresponse == 0
        and current_execute_onfailure > 0
    ):
        result = 'rust_primary_java_replica_branch_remaining_unknown_matches_existing_full_opensearch_read_starvation_practical_stop'
    else:
        result = 'inconclusive'

    print(f'checker_result={result}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
