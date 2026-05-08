#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


if len(sys.argv) != 2:
    print(
        'usage: check_invoke_exceptions_match_repeated_fanout_on_partially_closed_connections.py <probe-report.json>',
        file=sys.stderr,
    )
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
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

conn_by_port = {}
for line in lines:
    m = re.search(
        r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\] channel '
        r'\[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), remoteAddress=.*127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\}\]',
        line,
    )
    if m and '{rust-replica-1}' in line:
        conn_by_port[m.group(3)] = (int(m.group(1)), int(m.group(2)))

by_conn = {}
for line in lines:
    m = re.search(
        r'steelsearch_netty4tcpchannel_close_invoked channel \[\[id: .* L:/127\.0\.0\.1:(\d+) ! R:.*127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\]\] serverChannel \[(true|false)\] closeInvokeOrder \[(\d+)\]',
        line,
    )
    if not m:
        continue
    local_port = m.group(1)
    if local_port not in conn_by_port:
        continue
    conn, idx = conn_by_port[local_port]
    by_conn.setdefault(conn, []).append((int(m.group(3)), idx, local_port))

exception_rows = []
for conn, vals in sorted(by_conn.items()):
    vals.sort()
    first_idx = vals[0][1]
    min_idx = min(v[1] for v in vals)
    if first_idx == min_idx:
        continue
    min_pos = next(i for i, (_, idx, _) in enumerate(vals) if idx == min_idx)
    duplicate_indices = sorted({idx for _, idx, _ in vals if sum(1 for _, j, _ in vals if j == idx) > 1})
    exception_rows.append(
        {
            'conn': conn,
            'first_idx': first_idx,
            'min_idx': min_idx,
            'first_order': vals[0][0],
            'min_order': vals[min_pos][0],
            'order_gap': vals[min_pos][0] - vals[0][0],
            'invoke_count': len(vals),
            'duplicate_indices': duplicate_indices,
            'sequence': [(order, idx) for order, idx, _ in vals],
        }
    )

large_gap_count = sum(1 for row in exception_rows if row['order_gap'] >= 100)
duplicate_index_count = sum(1 for row in exception_rows if row['duplicate_indices'])

print(f'failure_port={failure_port}')
print(f'exception_count={len(exception_rows)}')
print(f'large_gap_count={large_gap_count}')
print(f'duplicate_index_count={duplicate_index_count}')
print(f'rows={exception_rows}')
if len(exception_rows) > 0 and large_gap_count == len(exception_rows):
    print('result=invoke_exceptions_best_match_repeated_or_concurrent_fanout_on_partially_pre_closed_connections')
else:
    print('result=invoke_exceptions_do_not_cleanly_match_repeated_fanout')
