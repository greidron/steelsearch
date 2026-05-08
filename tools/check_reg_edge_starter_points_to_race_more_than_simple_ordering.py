#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_reg_edge_starter_points_to_race_more_than_simple_ordering.py <stdout.log>', file=sys.stderr)
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

orders = {}
for idx, line in enumerate(lines, start=1):
    if 275 <= idx <= 335 and f'127.0.0.1/127.0.0.1:{port}' in line and 'node connection [2] observed close on channelIndex' in line:
        m = re.search(r'channelIndex \[(\d+)\].*closeOrder \[(\d+)\]', line)
        if m:
            orders[int(m.group(1))] = int(m.group(2))

edge_orders = {k: orders.get(k) for k in (7, 12)}
low_orders = {k: orders.get(k) for k in (1, 2, 5)}
result = 'inconclusive'
if edge_orders[12] is not None and edge_orders[7] is not None and edge_orders[12] < edge_orders[7] and max(edge_orders.values()) < min(v for v in low_orders.values() if v is not None):
    result = 'reg_edge_slot_starter_points_to_partial_concurrent_race_more_than_simple_static_ordering'

print(f'rust_port = {port}')
print(f'edge_orders = {edge_orders}')
print(f'low_orders = {low_orders}')
print(f'result = {result}')
