#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from statistics import median

if len(sys.argv) != 2:
    print('usage: check_low_index_first_close_precedes_next_named_reconnect.py <probe-report.json>', file=sys.stderr)
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
stdout_log = Path(report['work_dir']) / 'opensearch' / 'stdout.log'
lines = stdout_log.read_text(errors='ignore').splitlines()

port = None
for line in lines:
    if 'steelsearch_publication_response_class=transport_failure' in line:
        m = re.search(r'\{127\.0\.0\.1:(\d+)\}', line)
        if m:
            port = m.group(1)
            break
if port is None:
    print('result=missing_failure_port')
    sys.exit(1)

named_opens = []
first_low_close = {}
for i, line in enumerate(lines):
    m = re.search(r'opened transport connection \[(\d+)\] to \[(.+)\] using channels', line)
    if m and f'127.0.0.1:{port}' in line and m.group(2).startswith('{rust-replica-1}'):
        named_opens.append((i, int(m.group(1))))
    m = re.search(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\]', line)
    if m and f'127.0.0.1:{port}' in line and '{rust-replica-1}' in line:
        conn = int(m.group(1))
        idx = int(m.group(2))
        if idx in (1, 2, 5, 6) and conn not in first_low_close:
            first_low_close[conn] = i

before_next_named = 0
next_named_before_first_low = 0
next_named_after_first_low_gaps = []
for idx, (open_i, conn) in enumerate(named_opens):
    if conn not in first_low_close:
        continue
    first_low_i = first_low_close[conn]
    next_open_i = named_opens[idx + 1][0] if idx + 1 < len(named_opens) else None
    if next_open_i is None or first_low_i < next_open_i:
        before_next_named += 1
        if next_open_i is not None:
            next_named_after_first_low_gaps.append(next_open_i - first_low_i)
    else:
        next_named_before_first_low += 1

print(f'named_connection_count_with_low_index_first={before_next_named + next_named_before_first_low}')
print(f'first_low_before_next_named_open_count={before_next_named}')
print(f'next_named_open_before_first_low_count={next_named_before_first_low}')
if next_named_after_first_low_gaps:
    print('next_named_open_after_first_low_lines=' + str({'min': min(next_named_after_first_low_gaps), 'median': median(next_named_after_first_low_gaps), 'max': max(next_named_after_first_low_gaps)}))

if next_named_before_first_low == 0 and before_next_named > 0:
    print('result=low_index_first_close_starts_before_any_later_named_reconnect_and_points_away_from_redundant_reconnect_replacement')
else:
    print('result=low_index_first_close_may_still_be_explained_by_later_named_reconnect_replacement')
