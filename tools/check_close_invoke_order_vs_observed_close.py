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


if len(sys.argv) != 2:
    print('usage: check_close_invoke_order_vs_observed_close.py <probe-report.json>', file=sys.stderr)
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

first_observed_by_conn = {}
conn_by_local_port = {}
for i, line in enumerate(lines):
    m = re.search(
        r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\] channel '
        r'\[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), remoteAddress=.*127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\}\]',
        line,
    )
    if m and '{rust-replica-1}' in line:
        conn = int(m.group(1))
        idx = int(m.group(2))
        local_port = m.group(3)
        conn_by_local_port[local_port] = conn
        first_observed_by_conn.setdefault(conn, (idx, local_port, i))

first_invoked_by_conn = {}
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
    if conn is None or conn in first_invoked_by_conn:
        continue
    observed = first_observed_by_conn.get(conn)
    if observed is None:
        continue
    idx = observed[0] if observed[1] == local_port else None
    if idx is None:
        # resolve current local_port -> idx within the same connection
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
    first_invoked_by_conn[conn] = (idx, local_port, int(m.group(3)), i)

same_index = 0
different_index = 0
invoke_family_counts = Counter()
observed_family_counts = Counter()
delta_counter = Counter()
sample = []

for conn, observed in sorted(first_observed_by_conn.items()):
    invoked = first_invoked_by_conn.get(conn)
    if invoked is None:
        continue
    observed_idx, observed_port, observed_line = observed
    invoked_idx, invoked_port, invoke_order, invoke_line = invoked
    observed_family = family_for_index(observed_idx)
    invoked_family = family_for_index(invoked_idx)
    observed_family_counts[observed_family] += 1
    invoke_family_counts[invoked_family] += 1
    if observed_idx == invoked_idx:
        same_index += 1
    else:
        different_index += 1
    delta_counter[f'{invoked_idx}->{observed_idx}'] += 1
    if len(sample) < 5:
        sample.append(
            {
                'conn': conn,
                'invoked_idx': invoked_idx,
                'observed_idx': observed_idx,
                'invoked_family': invoked_family,
                'observed_family': observed_family,
                'invoke_order': invoke_order,
            }
        )

print(f'failure_port={failure_port}')
print(f'observed_connection_count={len(first_observed_by_conn)}')
print(f'invoked_connection_count={len(first_invoked_by_conn)}')
print(f'same_index_count={same_index}')
print(f'different_index_count={different_index}')
print(f'invoke_family_counts={dict(invoke_family_counts)}')
print(f'observed_family_counts={dict(observed_family_counts)}')
print(f'index_transition_counts={dict(delta_counter)}')
print(f'sample={sample}')

if same_index == len(first_invoked_by_conn) and invoke_family_counts == observed_family_counts:
    print('result=close_iteration_order_matches_first_observed_close_more_directly_than_callback_race')
elif different_index >= max(1, len(first_invoked_by_conn) // 4):
    print('result=close_callback_completion_race_contributes_more_directly_than_simple_close_iteration_order')
else:
    print('result=close_iteration_and_callback_race_are_mixed')
