#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
port = None
for line in lines:
    m = re.search(r'rootCauseMessage=\[rust-replica-1\]\[127\.0\.0\.1:(\d+)\]\[internal:cluster/coordination/publish_state\] disconnected', line)
    if m:
        port = m.group(1)
        break
conn_first = {}
idle = []
for line in lines:
    m = re.search(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\].*remoteAddress=/127\.0\.0\.1:(\d+)\}.*idleForMs \[(\d+)\].*closeOrder \[(\d+)\]', line)
    if not m:
        continue
    conn_id, idx, remote_port, idle_ms, close_order = int(m.group(1)), int(m.group(2)), m.group(3), int(m.group(4)), int(m.group(5))
    if port and remote_port != port:
        continue
    if conn_id not in conn_first or close_order < conn_first[conn_id]['close_order']:
        conn_first[conn_id] = {'index': idx, 'idle_ms': idle_ms, 'close_order': close_order}

index_counts = Counter(v['index'] for v in conn_first.values())
idle_zero = sum(1 for v in conn_first.values() if v['idle_ms'] == 0)
summary = {
    'rust_port': port,
    'connection_count': len(conn_first),
    'first_index_counts': dict(index_counts),
    'idle_zero_count': idle_zero,
}
summary['result'] = 'native_join_initial_close_event_points_away_from_low_index_stale_sibling' if (
    len(conn_first) > 0 and
    index_counts.get(0, 0) >= max(1, len(conn_first) // 2) and
    idle_zero == len(conn_first)
) else 'inconclusive'
print(json.dumps(summary, indent=2))
