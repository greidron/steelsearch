#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path


def family_for_index(idx: int) -> str:
    if 0 <= idx <= 2:
        return 'BULK'
    if idx == 3:
        return 'PING'
    if idx == 4:
        return 'STATE'
    if 5 <= idx <= 6:
        return 'RECOVERY'
    if 7 <= idx <= 12:
        return 'REG'
    return 'UNKNOWN'


if len(sys.argv) != 3:
    print(
        'usage: check_invoke_skew_matches_ordered_iteration_with_earlier_skip.py <probe-report.json> <tcptransport.java>',
        file=sys.stderr,
    )
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
tcptransport = Path(sys.argv[2]).read_text()
stdout_log = Path(report['work_dir']) / 'opensearch' / 'stdout.log'
lines = stdout_log.read_text(errors='ignore').splitlines()

failure_port = None
for line in lines:
    if 'steelsearch_publication_response_class=transport_failure' in line:
        m = re.search(r'\{127\.0\.0\.1:(\d+)\}', line)
        if m:
            failure_port = m.group(1)
            break
if failure_port is None:
    print('result=missing_failure_port')
    sys.exit(1)

conn_by_local_port = {}
for line in lines:
    m = re.search(
        r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\] channel '
        r'\[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), remoteAddress=.*127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\}\]',
        line,
    )
    if m and '{rust-replica-1}' in line:
        conn_by_local_port[m.group(3)] = int(m.group(1))

invoked_indices_by_conn = {}
for i, line in enumerate(lines):
    m = re.search(
        r'steelsearch_netty4tcpchannel_close_invoked channel \[\[id: .* L:/127\.0\.0\.1:(\d+) ! R:.*127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\]\] serverChannel \[(true|false)\] closeInvokeOrder \[(\d+)\]',
        line,
    )
    if not m:
        continue
    local_port = m.group(1)
    conn = conn_by_local_port.get(local_port)
    if conn is None:
        continue
    idx = None
    for line2 in lines:
        m2 = re.search(
            r'node connection \[' + str(conn) + r'\] observed close on channelIndex \[(\d+)\] channel '
            r'\[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:' + re.escape(local_port) + r', remoteAddress=.*127\.0\.0\.1:' + re.escape(failure_port) + r'\}\]',
            line2,
        )
        if m2 and '{rust-replica-1}' in line2:
            idx = int(m2.group(1))
            break
    if idx is None:
        continue
    invoked_indices_by_conn.setdefault(conn, []).append((int(m.group(3)), idx))

first_eq_min = 0
first_ne_min = 0
min_family_counts = Counter()
first_family_counts = Counter()
sample = []

for conn, values in sorted(invoked_indices_by_conn.items()):
    values.sort()
    first_idx = values[0][1]
    min_idx = min(idx for _, idx in values)
    first_family_counts[family_for_index(first_idx)] += 1
    min_family_counts[family_for_index(min_idx)] += 1
    if first_idx == min_idx:
        first_eq_min += 1
    else:
        first_ne_min += 1
    if len(sample) < 5:
        sample.append({'conn': conn, 'first_idx': first_idx, 'min_idx': min_idx, 'invoked_indices': [idx for _, idx in values[:8]]})

print(f'failure_port={failure_port}')
print(f'connection_count={len(invoked_indices_by_conn)}')
print(f'first_eq_min_count={first_eq_min}')
print(f'first_ne_min_count={first_ne_min}')
print(f'first_family_counts={dict(first_family_counts)}')
print(f'min_family_counts={dict(min_family_counts)}')
print(f"source_nodechannels_close_calls_closechannels={'CloseableChannel.closeChannels(channels, block);' in tcptransport}")
print(f'sample={sample}')

if first_eq_min >= max(1, len(invoked_indices_by_conn) - 8):
    print('result=invoke_skew_best_matches_ordered_iteration_with_earlier_lower_index_skip')
else:
    print('result=invoke_skew_is_not_explained_by_simple_ordered_iteration_with_skip')
