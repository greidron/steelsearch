#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from statistics import median

if len(sys.argv) != 2:
    print(
        'usage: check_publication_failure_tracks_reg_tail_not_low_index_first_close.py <probe-report.json>',
        file=sys.stderr,
    )
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
stdout_log = Path(report['work_dir']) / 'opensearch' / 'stdout.log'
lines = stdout_log.read_text(errors='ignore').splitlines()

failure_rows = []
failure_port = None
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
closes_by_conn = {}
for i, line in enumerate(lines):
    m = re.search(r'opened transport connection \[(\d+)\] to \[(.+)\] using channels', line)
    if m and f'127.0.0.1:{failure_port}' in line and m.group(2).startswith('{rust-replica-1}'):
        named_opens.append((i, int(m.group(1))))

    m = re.search(
        r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\].*closeOrder \[(\d+)\]',
        line,
    )
    if m and f'127.0.0.1:{failure_port}' in line and '{rust-replica-1}' in line:
        conn = int(m.group(1))
        idx = int(m.group(2))
        order = int(m.group(3))
        closes_by_conn.setdefault(conn, []).append((i, idx, order))

first_close_gaps = []
state_close_gaps = []
reg_tail_gaps = []
last_close_gaps = []
low_index_first_count = 0
closest_preceding_reg_family_count = 0
closest_preceding_non_reg_count = 0

for failure_i in failure_rows:
    conn = None
    for open_i, open_conn in reversed(named_opens):
        if open_i < failure_i:
            conn = open_conn
            break
    if conn is None:
        continue

    closes = [row for row in closes_by_conn.get(conn, []) if row[0] < failure_i]
    if not closes:
        continue

    first_close = closes[0]
    last_close = closes[-1]
    first_close_gaps.append(failure_i - first_close[0])
    last_close_gaps.append(failure_i - last_close[0])

    if first_close[1] in (1, 2, 5, 6):
        low_index_first_count += 1

    state_closes = [row for row in closes if row[1] == 4]
    if state_closes:
        state_close_gaps.append(failure_i - state_closes[-1][0])

    reg_closes = [row for row in closes if 7 <= row[1] <= 12]
    if reg_closes:
        reg_tail = reg_closes[-1]
        reg_tail_gaps.append(failure_i - reg_tail[0])

    closest = closes[-1]
    if 7 <= closest[1] <= 12:
        closest_preceding_reg_family_count += 1
    else:
        closest_preceding_non_reg_count += 1

print(f'failure_port={failure_port}')
print(f'failure_row_count={len(failure_rows)}')
print(f'low_index_first_count={low_index_first_count}')
print(
    'first_close_to_failure_lines='
    + str({'min': min(first_close_gaps), 'median': median(first_close_gaps), 'max': max(first_close_gaps)})
)
print(
    'last_close_to_failure_lines='
    + str({'min': min(last_close_gaps), 'median': median(last_close_gaps), 'max': max(last_close_gaps)})
)
if state_close_gaps:
    print(
        'state_close_to_failure_lines='
        + str({'min': min(state_close_gaps), 'median': median(state_close_gaps), 'max': max(state_close_gaps)})
    )
if reg_tail_gaps:
    print(
        'reg_tail_close_to_failure_lines='
        + str({'min': min(reg_tail_gaps), 'median': median(reg_tail_gaps), 'max': max(reg_tail_gaps)})
    )
print(f'closest_preceding_reg_family_count={closest_preceding_reg_family_count}')
print(f'closest_preceding_non_reg_count={closest_preceding_non_reg_count}')

if median(reg_tail_gaps) < median(first_close_gaps) and closest_preceding_reg_family_count >= len(failure_rows) - 3:
    print('result=publication_failure_tracks_reg_tail_or_final_teardown_more_directly_than_low_index_first_close')
else:
    print('result=publication_failure_still_ambiguous_between_first_close_and_tail_close')
