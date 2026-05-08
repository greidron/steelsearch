#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 4:
    print('usage: check_publish_state_closefuture_points_away_from_java_unused_cleanup.py <stdout.log> <ClusterConnectionManager.java> <Netty4Transport.java>', file=sys.stderr)
    sys.exit(2)

log_text = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
ccm_text = Path(sys.argv[2]).read_text(encoding='utf-8', errors='replace')
netty_text = Path(sys.argv[3]).read_text(encoding='utf-8', errors='replace')
lines = log_text.splitlines()

port = '52561'
first_disconnect_line = None
selected_before_disconnect = set()

sel_re = re.compile(r'action-tagged selected channel index \[(\d+)\].*remoteAddress=.*:' + port)
hint_re = re.compile(r'netty4 tcp channel close completed for \[\[id: .* L:/127\.0\.0\.1:(\d+) ! R:.*:' + port + r'\]\] with hint \[(.+)\]')
invoke_re = re.compile(r'steelsearch_netty4tcpchannel_close_invoked channel \[\[id: .* L:/127\.0\.0\.1:(\d+) .*:' + port + r'\]\]')

hint_lines = {}
invoke_lines = {}
for lineno, line in enumerate(lines, start=1):
    if first_disconnect_line is None and 'FollowerChecker{' in line and 'disconnected' in line and port in line:
        first_disconnect_line = lineno
    if first_disconnect_line is None:
        m = sel_re.search(line)
        if m:
            selected_before_disconnect.add(int(m.group(1)))
    m = hint_re.search(line)
    if m:
        hint_lines[m.group(1)] = (lineno, m.group(2))
    m = invoke_re.search(line)
    if m:
        invoke_lines[m.group(1)] = lineno

starter_ports = {'43372': 12, '43308': 1}
starter_unselected = all(idx not in selected_before_disconnect for idx in starter_ports.values())
closefuture_before_invoke = 0
for local in starter_ports:
    hint_line, hint_name = hint_lines.get(local, (None, None))
    invoke_line = invoke_lines.get(local)
    if hint_name == 'closeFutureIntercepted' and hint_line is not None and (invoke_line is None or hint_line <= invoke_line):
        closefuture_before_invoke += 1

source_has_early_closefuture_listener = 'addEarlyCloseFutureHintListener' in netty_text and 'closeFutureIntercepted' in netty_text
source_has_whole_connection_closeinternal = 'closeInternal()' in ccm_text and 'IOUtils.closeWhileHandlingException(next.getValue())' in ccm_text
source_has_unused_idle_cleanup_symbol = any(token in ccm_text for token in ['closeIdle', 'unused', 'stale sibling'])

result = 'undetermined'
if starter_unselected and closefuture_before_invoke == 2 and source_has_early_closefuture_listener and source_has_whole_connection_closeinternal and not source_has_unused_idle_cleanup_symbol:
    result = 'publish_state_closefuture_starter_points_away_from_java_unused_channel_cleanup_and_toward_peer_side_first_close_on_never_access_siblings'

print(f'first_disconnect_line={first_disconnect_line}')
print(f'selected_before_disconnect={sorted(selected_before_disconnect)}')
print(f'starter_unselected={starter_unselected}')
print(f'closefuture_before_invoke={closefuture_before_invoke}')
print(f'source_has_early_closefuture_listener={source_has_early_closefuture_listener}')
print(f'source_has_whole_connection_closeinternal={source_has_whole_connection_closeinternal}')
print(f'source_has_unused_idle_cleanup_symbol={source_has_unused_idle_cleanup_symbol}')
print(f'result={result}')
