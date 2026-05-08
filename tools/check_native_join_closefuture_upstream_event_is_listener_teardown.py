#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 3:
    print('usage: check_native_join_closefuture_upstream_event_is_listener_teardown.py <stdout.log> <TcpTransport.java>', file=sys.stderr)
    sys.exit(2)

log_path = Path(sys.argv[1])
tcp_path = Path(sys.argv[2])
lines = log_path.read_text(errors='replace').splitlines()
tcp = tcp_path.read_text(errors='replace')

open_line = None
port = None
for idx, line in enumerate(lines, start=1):
    if 'opened transport connection' in line and 'rust-replica-1' in line:
        open_line = idx
        m = re.search(r'127\.0\.0\.1:(\d+)\}\{dimr\}', line)
        if m:
            port = m.group(1)
            break
if open_line is None or port is None:
    raise SystemExit('could not find rust opened transport connection')

window = []
for idx in range(open_line, min(open_line + 80, len(lines) + 1)):
    line = lines[idx - 1]
    if f'127.0.0.1:{port}' in line:
        window.append((idx, line))

selected_before = sum(1 for _, line in window if 'action-tagged selected channel index' in line)
closefuture_ports = []
for idx, line in window:
    if 'close completed' in line and 'closeFutureIntercepted' in line:
        m = re.search(r'L:/127\.0\.0\.1:(\d+)', line)
        if m:
            closefuture_ports.append((m.group(1), idx))

listener_marker = 'callerGreatGreatGreatGrandparent [org.opensearch.transport.TcpTransport$ChannelsConnectedListener#lambda$onResponse$0:1123]'
matched_caller = 0
for local_port, idx0 in closefuture_ports:
    found = False
    for idx, line in window:
        if abs(idx - idx0) <= 15 and f'L:/127.0.0.1:{local_port}' in line and listener_marker in line:
            found = True
            break
    if found:
        matched_caller += 1

result = 'inconclusive'
if closefuture_ports and matched_caller == len(closefuture_ports) and selected_before > 0:
    result = 'native_join_closefuture_upstream_event_points_away_from_connect_future_failure_and_toward_response_listener_teardown'

print(f'rust_port = {port}')
print(f'open_line = {open_line}')
print(f'action_selected_before_close_count = {selected_before}')
print(f'closefutureintercepted_count = {len(closefuture_ports)}')
print(f'matched_listener_teardown_caller_count = {matched_caller}')
print(f'source_listener_calls_nodechannels_close = {'nodeChannels.close();' in tcp}')
print(f'result = {result}')
