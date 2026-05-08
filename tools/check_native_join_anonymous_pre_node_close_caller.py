#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_native_join_anonymous_pre_node_close_caller.py <stdout.log>', file=sys.stderr)
    sys.exit(2)

lines = Path(sys.argv[1]).read_text(errors='replace').splitlines()
port = None
for line in lines:
    if 'opened transport connection [1]' in line:
        m = re.search(r'127\.0\.0\.1:(\d+)\}\{Y', line)
        if m:
            port = m.group(1)
            break
if port is None:
    for line in lines:
        if 'opened transport connection [1]' in line:
            m = re.search(r'127\.0\.0\.1:(\d+)\}\{', line)
            if m:
                port = m.group(1)
                break
if port is None:
    raise SystemExit('could not determine handshake port')

caller_line = None
close_line = None
for idx, line in enumerate(lines, start=1):
    if caller_line is None and f'R:/127.0.0.1:{port}' in line and 'steelsearch_netty4tcpchannel_close_caller' in line and 'HandshakingTransportAddressConnector$1$1$1#innerOnResponse:140' in line:
        caller_line = (idx, line)
    if close_line is None and 'node connection [1] observed close' in line and f'/127.0.0.1:{port}' in line:
        close_line = (idx, line)

result = 'inconclusive'
if caller_line and close_line and caller_line[0] <= close_line[0]:
    result = 'native_join_anonymous_pre_node_close_caller_points_to_handshake_response_completion_path'

print(f'handshake_port = {port}')
print(f'caller_line = {caller_line[0] if caller_line else None}')
print(f'close_line = {close_line[0] if close_line else None}')
print(f'caller_contains_innerOnResponse = {bool(caller_line and "HandshakingTransportAddressConnector$1$1$1#innerOnResponse:140" in caller_line[1])}')
print(f'caller_contains_closeWhileHandlingException = {bool(caller_line and "IOUtils#closeWhileHandlingException:179" in caller_line[1])}')
print(f'result = {result}')
