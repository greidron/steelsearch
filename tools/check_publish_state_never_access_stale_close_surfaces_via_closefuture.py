#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 4:
    print('usage: check_publish_state_never_access_stale_close_surfaces_via_closefuture.py <stdout.log> <Netty4Transport.java> <OutboundHandler.java>', file=sys.stderr)
    sys.exit(2)

log_text = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
netty_text = Path(sys.argv[2]).read_text(encoding='utf-8', errors='replace')
outbound_text = Path(sys.argv[3]).read_text(encoding='utf-8', errors='replace')
lines = log_text.splitlines()

first_disconnect_line = None
selected_before_disconnect = []
port = '52561'

sel_re = re.compile(r'action-tagged selected channel index \[(\d+)\].*remoteAddress=.*:' + port)
hint_re = re.compile(r'netty4 tcp channel close completed for \[\[id: .* L:/127\.0\.0\.1:(\d+) ! R:.*:' + port + r'\]\] with hint \[(.+)\]')
invoke_re = re.compile(r'steelsearch_netty4tcpchannel_close_invoked channel \[\[id: .* L:/127\.0\.0\.1:(\d+) .*:' + port + r'\]\]')
caller_re = re.compile(r'steelsearch_netty4tcpchannel_close_caller channel \[\[id: .* L:/127\.0\.0\.1:(\d+) .*:' + port + r'\]\]')
inactive_re = re.compile(r'channelInactive on \[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), remoteAddress=.*:' + port + r'\}\]')

hint_lines = {}
invoke_lines = {}
caller_lines = {}
inactive_lines = {}
for lineno, line in enumerate(lines, start=1):
    if first_disconnect_line is None and 'FollowerChecker{' in line and 'disconnected' in line and port in line:
        first_disconnect_line = lineno
    if first_disconnect_line is None:
        m = sel_re.search(line)
        if m:
            selected_before_disconnect.append(int(m.group(1)))
    m = hint_re.search(line)
    if m:
        hint_lines[m.group(1)] = (lineno, m.group(2))
    m = invoke_re.search(line)
    if m:
        invoke_lines[m.group(1)] = lineno
    m = caller_re.search(line)
    if m:
        caller_lines[m.group(1)] = lineno
    m = inactive_re.search(line)
    if m:
        inactive_lines[m.group(1)] = lineno

starter_ports = {'43372': 12, '43308': 1}
closefuture_before_invoke = 0
inactive_after_hint = 0
for local in starter_ports:
    hint_line, hint_name = hint_lines.get(local, (None, None))
    invoke_line = invoke_lines.get(local)
    caller_line = caller_lines.get(local)
    inactive_line = inactive_lines.get(local)
    if hint_name == 'closeFutureIntercepted' and hint_line is not None and (invoke_line is None or hint_line <= invoke_line):
        closefuture_before_invoke += 1
    if hint_line is not None and inactive_line is not None and inactive_line >= hint_line:
        inactive_after_hint += 1

selected_set = sorted(set(selected_before_disconnect))
starter_unselected = all(idx not in selected_set for idx in starter_ports.values())
source_early_closefuture_listener_sets_closefutureintercepted = 'addEarlyCloseFutureHintListener' in netty_text and 'closeFutureIntercepted' in netty_text
source_send_marks_accessed = 'markAccessed' in outbound_text

result = 'undetermined'
if starter_unselected and closefuture_before_invoke == 2 and inactive_after_hint == 2 and source_early_closefuture_listener_sets_closefutureintercepted and source_send_marks_accessed:
    result = 'publish_state_never_access_stale_siblings_surface_via_early_closefuture_before_local_close_more_than_via_explicitlocalclose'

print(f'first_disconnect_line={first_disconnect_line}')
print(f'selected_before_disconnect={selected_set}')
print(f'starter_unselected={starter_unselected}')
print(f'closefuture_before_invoke={closefuture_before_invoke}')
print(f'inactive_after_hint={inactive_after_hint}')
print(f'source_early_closefuture_listener_sets_closefutureintercepted={source_early_closefuture_listener_sets_closefutureintercepted}')
print(f'source_send_marks_accessed={source_send_marks_accessed}')
print(f'result={result}')
