#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_publish_state_fanout_closefuture_origin.py <stdout.log>', file=sys.stderr)
    sys.exit(2)

lines = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace').splitlines()

publish_add_line = None
first_disconnect_line = None
conn2_open_line = None
port = None
conn2_channels = {}
first_three = []
anon_closefuture_before_conn2 = 0

port_re = re.compile(r'\{127\.0\.0\.1:(\d+)\}')
channel_re = re.compile(r'localAddress=/127\.0\.0\.1:(\d+), remoteAddress=127\.0\.0\.1/127\.0\.0\.1:(\d+)')
obs_re = re.compile(r'node connection \[2\] observed close on channelIndex \[(\d+)\].*localAddress=/127\.0\.0\.1:(\d+), remoteAddress=127\.0\.0\.1/127\.0\.0\.1:(\d+).*closeOrder \[(\d+)\]')
hint_re = re.compile(r'netty4 tcp channel close completed for \[\[id: .* L:/127\.0\.0\.1:(\d+) ! R:(?:127\.0\.0\.1/)?127\.0\.0\.1:(\d+)\]\] with hint \[(.+)\]')

hint_by_local = {}
for idx, line in enumerate(lines, start=1):
    m = hint_re.search(line)
    if m:
        hint_by_local.setdefault((m.group(1), m.group(2)), []).append((idx, m.group(3)))

for idx, line in enumerate(lines, start=1):
    if publish_add_line is None and 'steelsearch_transport_response_context=add' in line and 'action=internal:cluster/coordination/publish_state' in line and 'node={rust-replica-1}' in line:
        publish_add_line = idx
        m = port_re.search(line)
        if m:
            port = m.group(1)
    if first_disconnect_line is None and 'FollowerChecker{' in line and 'disconnected' in line and 'rust-replica-1' in line:
        first_disconnect_line = idx
        if port is None:
            m = port_re.search(line)
            if m:
                port = m.group(1)
    if conn2_open_line is None and 'opened transport connection [2]' in line and 'rust-replica-1' in line:
        conn2_open_line = idx
        for ch_idx, m in enumerate(channel_re.finditer(line)):
            local, remote = m.groups()
            conn2_channels[local] = (ch_idx, remote)

if None in (publish_add_line, first_disconnect_line, conn2_open_line) or port is None:
    print('missing key markers', file=sys.stderr)
    sys.exit(1)

for idx, line in enumerate(lines[:conn2_open_line], start=1):
    if f'R:/127.0.0.1:{port}' in line and 'closeFutureIntercepted' in line:
        anon_closefuture_before_conn2 += 1

for idx, line in enumerate(lines[publish_add_line-1:first_disconnect_line], start=publish_add_line):
    m = obs_re.search(line)
    if not m:
        continue
    ch_idx, local, remote, order = m.groups()
    if remote != port:
        continue
    hint = 'unknown'
    for hint_line, hint_name in hint_by_local.get((local, remote), []):
        if hint_line >= idx:
            hint = hint_name
            break
    in_conn2 = local in conn2_channels and conn2_channels[local][1] == port
    conn2_index = conn2_channels[local][0] if in_conn2 else None
    first_three.append((int(order), int(ch_idx), local, hint, in_conn2, conn2_index))
    if len(first_three) == 3:
        break

same_conn_closefuture_starters = sum(1 for _, _, _, hint, in_conn2, _ in first_three if in_conn2 and hint == 'closeFutureIntercepted')
same_conn_explicit_starters = sum(1 for _, _, _, hint, in_conn2, _ in first_three if in_conn2 and hint == 'explicitLocalClose')

result = 'undetermined'
if len(first_three) >= 2 and all(item[4] for item in first_three[:2]) and same_conn_closefuture_starters >= 2:
    result = 'publish_state_closefuture_starter_is_same_named_connection_unused_sibling_stale_close_not_earlier_anonymous_probe_residue'

print(f'rust_port={port}')
print(f'publish_add_line={publish_add_line}')
print(f'conn2_open_line={conn2_open_line}')
print(f'first_disconnect_line={first_disconnect_line}')
print(f'anon_closefuture_before_conn2={anon_closefuture_before_conn2}')
print(f'first_three={first_three}')
print(f'same_conn_closefuture_starters={same_conn_closefuture_starters}')
print(f'same_conn_explicit_starters={same_conn_explicit_starters}')
print(f'result={result}')
