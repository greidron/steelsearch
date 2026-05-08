#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_named_conn2_starter_is_unselected_reg_not_low_index.py <stdout.log>', file=sys.stderr)
    sys.exit(2)

lines = Path(sys.argv[1]).read_text(errors='replace').splitlines()
port = None
open_idx = None
for idx, line in enumerate(lines, start=1):
    if 'opened transport connection [2]' in line and 'rust-replica-1' in line:
        open_idx = idx
        m = re.search(r'127\.0\.0\.1:(\d+)\}\{dimr\}', line)
        if m:
            port = m.group(1)
            break
if port is None:
    raise SystemExit('could not determine rust port')

closes = []
for idx, line in enumerate(lines[open_idx-1:], start=open_idx):
    if 'opened transport connection [3]' in line:
        break
    if f'127.0.0.1/127.0.0.1:{port}' in line and 'node connection [2] observed close on channelIndex' in line:
        m = re.search(r'channelIndex \[(\d+)\].*closeOrder \[(\d+)\]', line)
        if m:
            closes.append((int(m.group(1)), int(m.group(2)), idx))

unselected_reg = [x for x in closes if x[0] in {7, 12}]
low_index = [x for x in closes if x[0] in {1, 2, 5}]
first_reg_order = min((x[1] for x in unselected_reg), default=None)
first_low_order = min((x[1] for x in low_index), default=None)

result = 'inconclusive'
if first_reg_order is not None and first_low_order is not None and first_reg_order < first_low_order:
    result = 'named_conn2_first_causal_event_is_unselected_reg_before_low_index_non_action'

print(f'rust_port = {port}')
print(f'first_unselected_reg_order = {first_reg_order}')
print(f'first_low_index_order = {first_low_order}')
print(f'unselected_reg_indices_by_order = {[x[0] for x in sorted(unselected_reg, key=lambda x: x[1])]}')
print(f'low_index_indices_by_order = {[x[0] for x in sorted(low_index, key=lambda x: x[1])]}')
print(f'result = {result}')
