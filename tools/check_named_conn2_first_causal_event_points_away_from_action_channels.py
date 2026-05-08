#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_named_conn2_first_causal_event_points_away_from_action_channels.py <stdout.log>', file=sys.stderr)
    sys.exit(2)

lines = Path(sys.argv[1]).read_text(errors='replace').splitlines()
open_idx = None
port = None
for idx, line in enumerate(lines, start=1):
    if 'opened transport connection [2]' in line and 'rust-replica-1' in line:
        open_idx = idx
        m = re.search(r'127\.0\.0\.1:(\d+)\}\{dimr\}', line)
        if m:
            port = m.group(1)
            break
if open_idx is None or port is None:
    raise SystemExit('could not determine first named connection [2]')

end_idx = len(lines) + 1
for idx, line in enumerate(lines[open_idx:], start=open_idx + 1):
    if 'opened transport connection [3]' in line or ('opened transport connection [' in line and idx > open_idx + 1 and 'rust-replica-1' in line):
        end_idx = idx
        break

selected = []
closes = []
for idx in range(open_idx, end_idx):
    line = lines[idx - 1]
    if f'127.0.0.1/127.0.0.1:{port}' in line and 'action-tagged selected channel index' in line:
        m = re.search(r'index \[(\d+)\] type \[(\w+)\] action \[([^\]]+)\]', line)
        if m:
            selected.append((int(m.group(1)), m.group(2), m.group(3), idx))
    if f'127.0.0.1/127.0.0.1:{port}' in line and 'node connection [2] observed close on channelIndex' in line:
        m = re.search(r'channelIndex \[(\d+)\].*closeOrder \[(\d+)\]', line)
        if m:
            closes.append((int(m.group(1)), int(m.group(2)), idx))

selected_idxs = {x[0] for x in selected}
first_five = sorted(closes, key=lambda x: x[1])[:5]
first_five_unselected = [x for x in first_five if x[0] not in selected_idxs]
state_ping_selected = sorted({x[0] for x in selected if x[1] in {'STATE', 'PING'}})
reg_selected = sorted({x[0] for x in selected if x[1] == 'REG'})

result = 'inconclusive'
if first_five and len(first_five_unselected) >= 3 and 3 not in [x[0] for x in first_five] and 4 not in [x[0] for x in first_five]:
    result = 'named_conn2_first_causal_event_points_away_from_publish_state_ping_and_toward_non_state_non_ping_channels'

print(f'rust_port = {port}')
print(f'conn2_open_line = {open_idx}')
print(f'selected_indices = {sorted(selected_idxs)}')
print(f'first_five_close_indices = {[x[0] for x in first_five]}')
print(f'first_five_close_orders = {[x[1] for x in first_five]}')
print(f'first_five_unselected_indices = {[x[0] for x in first_five_unselected]}')
print(f'state_ping_selected_indices = {state_ping_selected}')
print(f'reg_selected_indices = {reg_selected}')
print(f'result = {result}')
