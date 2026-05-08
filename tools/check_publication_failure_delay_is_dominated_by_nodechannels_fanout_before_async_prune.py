#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from statistics import median

if len(sys.argv) != 3:
    print(
        'usage: check_publication_failure_delay_is_dominated_by_nodechannels_fanout_before_async_prune.py '
        '<probe-report.json> <TransportService.java>',
        file=sys.stderr,
    )
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
transportservice = Path(sys.argv[2]).read_text()
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
first_close_by_conn = {}
closed_transport_by_conn = {}
for i, line in enumerate(lines):
    m = re.search(r'opened transport connection \[(\d+)\] to \[(.+)\] using channels', line)
    if m and f'127.0.0.1:{failure_port}' in line and m.group(2).startswith('{rust-replica-1}'):
        named_opens.append((i, int(m.group(1))))

    m = re.search(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\]', line)
    if m and f'127.0.0.1:{failure_port}' in line and '{rust-replica-1}' in line:
        conn = int(m.group(1))
        first_close_by_conn.setdefault(conn, i)

    m = re.search(r'closed transport connection \[(\d+)\] to \[\{rust-replica-1\}', line)
    if m and f'127.0.0.1:{failure_port}' in line:
        closed_transport_by_conn[int(m.group(1))] = i

first_to_closed = []
closed_to_failure = []
first_to_failure = []
for failure_i in failure_rows:
    conn = None
    for open_i, open_conn in reversed(named_opens):
        if open_i < failure_i:
            conn = open_conn
            break
    if conn is None:
        continue
    if conn not in first_close_by_conn or conn not in closed_transport_by_conn:
        continue
    first_close_i = first_close_by_conn[conn]
    closed_transport_i = closed_transport_by_conn[conn]
    if not (first_close_i < closed_transport_i < failure_i):
        continue
    first_to_closed.append(closed_transport_i - first_close_i)
    closed_to_failure.append(failure_i - closed_transport_i)
    first_to_failure.append(failure_i - first_close_i)

print(f'failure_port={failure_port}')
print(f'sample_count={len(first_to_closed)}')
print(f'source_uses_async_executor_for_nodedisconnected={"getExecutorService().execute" in transportservice}')
print('first_close_to_closed_transport_lines=' + str({'min': min(first_to_closed), 'median': median(first_to_closed), 'max': max(first_to_closed)}))
print('closed_transport_to_failure_lines=' + str({'min': min(closed_to_failure), 'median': median(closed_to_failure), 'max': max(closed_to_failure)}))
print('first_close_to_failure_lines=' + str({'min': min(first_to_failure), 'median': median(first_to_failure), 'max': max(first_to_failure)}))

if median(first_to_closed) > median(closed_to_failure) and 'getExecutorService().execute' in transportservice:
    print('result=publication_failure_delay_is_dominated_by_nodechannels_fanout_before_the_async_prune_tail')
else:
    print('result=publication_failure_delay_between_fanout_and_async_prune_is_still_ambiguous')
