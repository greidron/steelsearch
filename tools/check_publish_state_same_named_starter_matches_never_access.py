#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_publish_state_same_named_starter_matches_never_access.py <stdout.log>', file=sys.stderr)
    sys.exit(2)

lines = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace').splitlines()

selected = []
starters = []
conn_age_ms = None
port = None
first_disconnect_line = None

sel_re = re.compile(r'action-tagged selected channel index \[(\d+)\].*remoteAddress=127\.0\.0\.1/127\.0\.0\.1:(\d+)')
obs_re = re.compile(r'node connection \[2\] observed close on channelIndex \[(\d+)\].*remoteAddress=127\.0\.0\.1/127\.0\.0\.1:(\d+).*idleForMs \[(\d+)\] closeOrder \[(\d+)\]')
age_re = re.compile(r'closed transport connection \[2\].*age \[(\d+)ms\]')

for lineno, line in enumerate(lines, start=1):
    m = sel_re.search(line)
    if m and port is None:
        idx, port = m.groups()
    if m and m.group(2) == port and (first_disconnect_line is None or lineno < first_disconnect_line):
        selected.append(int(m.group(1)))
    if first_disconnect_line is None and 'FollowerChecker{' in line and 'disconnected' in line and 'rust-replica-1' in line:
        first_disconnect_line = lineno
    m = obs_re.search(line)
    if m:
        idx, remote, idle, order = m.groups()
        if port is None:
            port = remote
        if remote == port and int(order) <= 3:
            starters.append((int(order), int(idx), int(idle)))
    m = age_re.search(line)
    if m and conn_age_ms is None and 'rust-replica-1' in line:
        conn_age_ms = int(m.group(1))

selected_set = sorted(set(selected))
starter_indices = [idx for _, idx, _ in sorted(starters)]
starter_idle = {idx: idle for _, idx, idle in starters}
starter_unselected = all(idx not in selected_set for idx in starter_indices)
idle_matches_age = conn_age_ms is not None and all(idle == conn_age_ms for _, _, idle in starters)

result = 'undetermined'
if starter_indices and starter_unselected and idle_matches_age:
    result = 'publish_state_same_named_starter_matches_never_access_stale_close_more_than_same_connection_closefuture_race'

print(f'rust_port={port}')
print(f'selected_indices={selected_set}')
print(f'starter_indices={starter_indices}')
print(f'starter_idle={starter_idle}')
print(f'connection_age_ms={conn_age_ms}')
print(f'starter_unselected={starter_unselected}')
print(f'idle_matches_age={idle_matches_age}')
print(f'first_disconnect_line={first_disconnect_line}')
print(f'result={result}')
