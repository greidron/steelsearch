#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 4:
    print('usage: check_unselected_reg_stale_close_matches_never_selected_stale_access.py <stdout.log> <TcpTransport.java> <OutboundHandler.java>', file=sys.stderr)
    sys.exit(2)

log = Path(sys.argv[1]).read_text(errors='replace').splitlines()
tcp = Path(sys.argv[2]).read_text(errors='replace')
outbound = Path(sys.argv[3]).read_text(errors='replace')

port = None
for line in log:
    if 'opened transport connection [2]' in line and 'rust-replica-1' in line:
        m = re.search(r'127\.0\.0\.1:(\d+)\}\{dimr\}', line)
        if m:
            port = m.group(1)
            break
if port is None:
    raise SystemExit('could not determine rust port')

selected = set()
idle = {}
for idx, line in enumerate(log, start=1):
    if 275 <= idx <= 335 and f'127.0.0.1/127.0.0.1:{port}' in line and 'action-tagged selected channel index' in line:
        m = re.search(r'index \[(\d+)\]', line)
        if m:
            selected.add(int(m.group(1)))
    if 275 <= idx <= 335 and f'127.0.0.1/127.0.0.1:{port}' in line and 'node connection [2] observed close on channelIndex' in line:
        m = re.search(r'channelIndex \[(\d+)\].*idleForMs \[(\d+)\]', line)
        if m:
            idle[int(m.group(1))] = int(m.group(2))

starter_idxs = [7, 12]
starter_never_selected = all(i not in selected for i in starter_idxs)
starter_idle = {i: idle.get(i) for i in starter_idxs}
source_marks_on_open = 'Mark the channel init time' in tcp and 'markAccessed(relativeMillisTime);' in tcp
source_marks_on_send = 'channel.getChannelStats().markAccessed(threadPool.relativeTimeInMillis());' in outbound

result = 'inconclusive'
if starter_never_selected and all(starter_idle.get(i) == 600 for i in starter_idxs) and source_marks_on_open and source_marks_on_send:
    result = 'unselected_reg_stale_close_best_matches_never_selected_idle_sibling_stale_access'

print(f'rust_port = {port}')
print(f'selected_indices = {sorted(selected)}')
print(f'starter_never_selected = {starter_never_selected}')
print(f'starter_idle_ms = {starter_idle}')
print(f'source_marks_on_open = {source_marks_on_open}')
print(f'source_marks_on_send = {source_marks_on_send}')
print(f'result = {result}')
