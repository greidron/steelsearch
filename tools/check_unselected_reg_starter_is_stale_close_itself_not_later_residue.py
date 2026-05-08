#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_unselected_reg_starter_is_stale_close_itself_not_later_residue.py <stdout.log>', file=sys.stderr)
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

starter = {'local_port': '55142', 'index': 12, 'close_line': None, 'closefuture_line': None, 'caller_line': None}
for idx, line in enumerate(lines, start=1):
    if starter['close_line'] is None and 'node connection [2] observed close on channelIndex [12]' in line and f'127.0.0.1/127.0.0.1:{port}' in line:
        starter['close_line'] = idx
    if starter['closefuture_line'] is None and '55142' in line and 'closeFutureIntercepted' in line:
        starter['closefuture_line'] = idx
    if starter['caller_line'] is None and '55142' in line and 'ChannelsConnectedListener#lambda$onResponse$0:1123' in line:
        starter['caller_line'] = idx

result = 'inconclusive'
if starter['close_line'] and starter['closefuture_line'] and starter['caller_line'] and starter['close_line'] < starter['closefuture_line'] < starter['caller_line']:
    result = 'unselected_reg_starter_is_stale_close_itself_and_later_listener_fanout_is_residue'

print(f"rust_port = {port}")
print(f"starter_index = {starter['index']}")
print(f"starter_local_port = {starter['local_port']}")
print(f"starter_close_line = {starter['close_line']}")
print(f"starter_closefuture_line = {starter['closefuture_line']}")
print(f"starter_caller_line = {starter['caller_line']}")
print(f"result = {result}")
