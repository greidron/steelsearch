#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
rust_port = None
for line in lines:
    m = re.search(r'rootCauseMessage=\[rust-replica-1\]\[127\.0\.0\.1:(\d+)\]\[internal:cluster/coordination/publish_state\] disconnected', line)
    if m:
        rust_port = m.group(1)
        break
first_named = None
for line in lines:
    if 'node connection [' not in line or 'observed close on channelIndex' not in line or 'rust-replica-1' not in line or f':{rust_port}' not in line:
        continue
    conn_id = int(re.search(r'node connection \[(\d+)\]', line).group(1))
    idx = int(re.search(r'channelIndex \[(\d+)\]', line).group(1))
    idle = int(re.search(r'idleForMs \[(\d+)\]', line).group(1))
    order = int(re.search(r'closeOrder \[(\d+)\]', line).group(1))
    peer = re.search(r'for \[(.*?)\] serverChannel', line).group(1)
    if first_named is None or order < first_named['close_order']:
        first_named = {
            'connection_id': conn_id,
            'channel_index': idx,
            'peer': peer,
            'idle_ms': idle,
            'close_order': order,
        }
summary = {'rust_port': rust_port, 'first_named_close': first_named}
summary['result'] = 'native_join_initial_close_points_away_from_probe_connection' if (
    first_named is not None and first_named['connection_id'] != 1 and 'rust-replica-1' in first_named['peer']
) else 'inconclusive'
print(json.dumps(summary, indent=2))
