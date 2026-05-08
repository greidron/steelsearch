#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path
from statistics import median

if len(sys.argv) != 2:
    print(
        'usage: check_publish_state_failure_matches_nodeconnection_teardown_not_probe_family.py <probe-report.json>',
        file=sys.stderr,
    )
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
stdout_log = Path(report['work_dir']) / 'opensearch' / 'stdout.log'
lines = stdout_log.read_text(errors='ignore').splitlines()

failure_port = None
failure_rows = []
for i, line in enumerate(lines):
    if 'steelsearch_publication_response_class=transport_failure' not in line:
        continue
    m = re.search(r'\{127\.0\.0\.1:(\d+)\}', line)
    if not m:
        continue
    port = m.group(1)
    if failure_port is None:
        failure_port = port
    if port == failure_port:
        failure_rows.append(i)

if not failure_rows:
    print('failure_row_count=0')
    print('result=missing_publication_transport_failure_rows')
    sys.exit(1)

named_opens = []
for i, line in enumerate(lines):
    m = re.search(r'opened transport connection \[(\d+)\] to \[(.+)\] using channels', line)
    if not m or f'127.0.0.1:{failure_port}' not in line:
        continue
    conn = int(m.group(1))
    target = m.group(2)
    if target.startswith('{rust-replica-1}'):
        named_opens.append((i, conn))

named_closes = []
for i, line in enumerate(lines):
    m = re.search(
        r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\].*closeOrder \[(\d+)\]',
        line,
    )
    if not m or f'127.0.0.1:{failure_port}' not in line:
        continue
    if '{rust-replica-1}' not in line:
        continue
    named_closes.append((i, int(m.group(1)), int(m.group(2)), int(m.group(3))))

prev_family = Counter()
next_family = Counter()
close_count_before_failure = []
closest_preceding_index = Counter()
closest_preceding_gap = []

for failure_i in failure_rows:
    family = 'none'
    closest_close = None
    for j in range(failure_i - 1, -1, -1):
        line = lines[j]
        if f'127.0.0.1:{failure_port}' not in line:
            continue
        if 'node connection [' in line and 'observed close on channelIndex' in line:
            family = 'named_node_close' if '{rust-replica-1}' in line else 'probe_node_close'
            if '{rust-replica-1}' in line:
                m_idx = re.search(r'channelIndex \[(\d+)\]', line)
                closest_preceding_index[int(m_idx.group(1))] += 1
                closest_preceding_gap.append(failure_i - j)
            break
        if 'opened transport connection [' in line:
            family = 'named_node_open' if 'to [{rust-replica-1}' in line else 'probe_open'
            break
    prev_family[family] += 1

    family = 'none'
    for j in range(failure_i + 1, len(lines)):
        line = lines[j]
        if f'127.0.0.1:{failure_port}' not in line:
            continue
        if 'node connection [' in line and 'observed close on channelIndex' in line:
            family = 'named_node_close' if '{rust-replica-1}' in line else 'probe_node_close'
            break
        if 'opened transport connection [' in line:
            family = 'named_node_open' if 'to [{rust-replica-1}' in line else 'probe_open'
            break
    next_family[family] += 1

    conn = None
    for open_i, open_conn in reversed(named_opens):
        if open_i < failure_i:
            conn = open_conn
            break
    if conn is None:
        continue
    before = [row for row in named_closes if row[1] == conn and row[0] < failure_i]
    close_count_before_failure.append(len(before))

print(f'failure_port={failure_port}')
print(f'failure_row_count={len(failure_rows)}')
print(f'prev_family_counts={dict(sorted(prev_family.items()))}')
print(f'next_family_counts={dict(sorted(next_family.items()))}')
print(f'closest_preceding_index_counts={dict(sorted(closest_preceding_index.items()))}')
if closest_preceding_gap:
    print(
        'closest_preceding_gap_ms_equivalent_lines='
        + str(
            {
                'min': min(closest_preceding_gap),
                'median': median(closest_preceding_gap),
                'max': max(closest_preceding_gap),
            }
        )
    )
if close_count_before_failure:
    dist = Counter(close_count_before_failure)
    print(f'close_count_before_failure_dist={dict(sorted(dist.items()))}')
    print(
        'close_count_before_failure_stats='
        + str(
            {
                'min': min(close_count_before_failure),
                'median': median(close_count_before_failure),
                'max': max(close_count_before_failure),
            }
        )
    )

if prev_family == Counter({'named_node_close': len(failure_rows)}) and median(close_count_before_failure) >= 12:
    print('result=publication_transport_failure_matches_node_connection_sibling_teardown_more_directly_than_singleton_probe_close')
else:
    print('result=publication_transport_failure_family_still_ambiguous')
