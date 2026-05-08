#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_handshake_probe_teardown_is_benign_vs_later_named_failure.py <stdout.log>', file=sys.stderr)
    sys.exit(2)

lines = Path(sys.argv[1]).read_text(errors='replace').splitlines()
port = None
for line in lines:
    if 'opened transport connection [2]' in line and 'rust-replica-1' in line:
        m = re.search(r'127\.0\.0\.1:(\d+)\}\{dimr\}', line)
        if m:
            port = m.group(1)
            break
if port is None:
    raise SystemExit('could not determine rust port')

conn1_close = conn1_closed = conn2_open = None
probe_caller = named_caller = None
for idx, line in enumerate(lines, start=1):
    if conn1_close is None and 'node connection [1] observed close' in line and f'/127.0.0.1:{port}' in line:
        conn1_close = (idx, line)
    if conn1_closed is None and 'closed transport connection [1]' in line and f'127.0.0.1:{port}' in line:
        conn1_closed = (idx, line)
    if conn2_open is None and 'opened transport connection [2]' in line and f'127.0.0.1:{port}' in line:
        conn2_open = (idx, line)
    if probe_caller is None and 'steelsearch_netty4tcpchannel_close_caller' in line and 'HandshakingTransportAddressConnector$1$1$1#innerOnResponse:140' in line and f'R:/127.0.0.1:{port}' in line:
        probe_caller = (idx, line)
    if named_caller is None and 'steelsearch_netty4tcpchannel_close_caller' in line and 'TcpTransport$ChannelsConnectedListener#lambda$onResponse$0:1123' in line and f'127.0.0.1/127.0.0.1:{port}' in line:
        named_caller = (idx, line)

result = 'inconclusive'
if conn1_closed and conn2_open and probe_caller and named_caller and conn1_closed[0] < conn2_open[0] < named_caller[0]:
    result = 'handshake_probe_teardown_looks_benign_and_not_the_same_direct_caller_chain_as_later_named_failure'

print(f'rust_port = {port}')
print(f'probe_caller_line = {probe_caller[0] if probe_caller else None}')
print(f'conn1_close_line = {conn1_close[0] if conn1_close else None}')
print(f'conn1_closed_line = {conn1_closed[0] if conn1_closed else None}')
print(f'conn2_open_line = {conn2_open[0] if conn2_open else None}')
print(f'named_failure_caller_line = {named_caller[0] if named_caller else None}')
print(f'result = {result}')
