#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_unselected_reg_starter_points_away_from_selected_reg_teardown.py <stdout.log>', file=sys.stderr)
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

selected_idxs = set()
for idx, line in enumerate(lines, start=1):
    if 275 <= idx <= 335 and f'127.0.0.1/127.0.0.1:{port}' in line and 'action-tagged selected channel index' in line:
        m = re.search(r'index \[(\d+)\]', line)
        if m:
            selected_idxs.add(int(m.group(1)))

ports = {'55110': 7, '55142': 12}
closefuture_before_caller = 0
for local_port, idx_num in ports.items():
    seen_closefuture = None
    seen_caller = None
    for idx, line in enumerate(lines, start=1):
        if local_port in line and 'closeFutureIntercepted' in line:
            seen_closefuture = idx
        if local_port in line and 'lambda$onResponse$0:1123' in line:
            seen_caller = idx
            break
    if seen_closefuture is not None and seen_caller is not None and seen_closefuture < seen_caller:
        closefuture_before_caller += 1

result = 'inconclusive'
if 7 not in selected_idxs and 12 not in selected_idxs and closefuture_before_caller >= 1:
    result = 'unselected_reg_starter_points_away_from_selected_reg_action_followup_and_toward_unused_reg_stale_or_fanout_residue'

print(f'rust_port = {port}')
print(f'selected_indices = {sorted(selected_idxs)}')
print(f'starter_indices_unselected = {7 not in selected_idxs and 12 not in selected_idxs}')
print(f'closefuture_before_caller_count = {closefuture_before_caller}')
print(f'result = {result}')
