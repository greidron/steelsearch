#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from statistics import median

if len(sys.argv) != 2:
    print(
        'usage: check_low_index_explicitlocalclose_begins_on_followup_node_connection_not_probe_epoch.py <probe-report.json>',
        file=sys.stderr,
    )
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
probe_opens = []
first_low_close = {}
for i, line in enumerate(lines):
    m = re.search(r'opened transport connection \[(\d+)\] to \[(.+)\] using channels', line)
    if m and f'127.0.0.1:{port}' in line:
        conn = int(m.group(1))
        target = m.group(2)
        if target.startswith('{rust-replica-1}'):
            named_opens.append((i, conn))
        elif target.startswith(f'{{127.0.0.1:{port}}}'):
            probe_opens.append((i, conn))

    m = re.search(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\]', line)
    if m and f'127.0.0.1:{port}' in line and '{rust-replica-1}' in line:
        conn = int(m.group(1))
        idx = int(m.group(2))
        if idx in (1, 2, 5, 6) and conn not in first_low_close:
            first_low_close[conn] = (i, idx)

before_probe_count = 0
probe_before_first_count = 0
probe_after_first_count = 0
open_to_low_gaps = []
open_to_probe_gaps = []
for open_i, conn in named_opens:
    if conn not in first_low_close:
        continue
    low_i, low_idx = first_low_close[conn]
    open_to_low_gaps.append(low_i - open_i)
    next_probe_i = None
    for probe_i, _ in probe_opens:
        if probe_i > open_i:
            next_probe_i = probe_i
            break
    if next_probe_i is None:
        before_probe_count += 1
        continue
    open_to_probe_gaps.append(next_probe_i - open_i)
    if next_probe_i < low_i:
        probe_before_first_count += 1
    else:
        probe_after_first_count += 1

print(f'failure_port={port}')
print(f'named_connection_count_with_low_index_first={len(open_to_low_gaps)}')
print(f'probe_before_first_low_close_count={probe_before_first_count}')
print(f'probe_after_first_low_close_count={probe_after_first_count}')
print(f'no_later_probe_count={before_probe_count}')
print('open_to_low_index_first_close_lines=' + str({'min': min(open_to_low_gaps), 'median': median(open_to_low_gaps), 'max': max(open_to_low_gaps)}))
if open_to_probe_gaps:
    print('open_to_next_probe_lines=' + str({'min': min(open_to_probe_gaps), 'median': median(open_to_probe_gaps), 'max': max(open_to_probe_gaps)}))

if probe_before_first_count == 0 and probe_after_first_count >= len(open_to_low_gaps) - 1:
    print('result=low_index_explicitlocalclose_begins_on_followup_multichannel_node_connection_not_on_singleton_probe_epoch')
else:
    print('result=low_index_explicitlocalclose_epoch_still_ambiguous_between_probe_and_followup_connection')
