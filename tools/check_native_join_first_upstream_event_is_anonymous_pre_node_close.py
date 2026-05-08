#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_native_join_first_upstream_event_is_anonymous_pre_node_close.py <stdout.log>', file=sys.stderr)
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
    raise SystemExit('could not determine rust port from connection [2]')

anon_close = None
conn2_open = None
first_conn2_closefuture = None
for idx, line in enumerate(lines, start=1):
    if anon_close is None and 'node connection [1] observed close' in line and f'/127.0.0.1:{port}' in line:
        anon_close = (idx, line)
    if conn2_open is None and 'opened transport connection [2]' in line and f'127.0.0.1:{port}' in line:
        conn2_open = (idx, line)
    if first_conn2_closefuture is None and 'closeFutureIntercepted' in line and f'127.0.0.1/127.0.0.1:{port}' in line:
        first_conn2_closefuture = (idx, line)

result = 'inconclusive'
if anon_close and conn2_open and first_conn2_closefuture and anon_close[0] < conn2_open[0] < first_conn2_closefuture[0]:
    result = 'native_join_first_upstream_event_is_anonymous_pre_node_connection_close'

print(f'rust_port = {port}')
print(f'anonymous_pre_node_close_line = {anon_close[0] if anon_close else None}')
print(f'conn2_open_line = {conn2_open[0] if conn2_open else None}')
print(f'first_conn2_closefuture_line = {first_conn2_closefuture[0] if first_conn2_closefuture else None}')
print(f'result = {result}')
