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
    print('usage: check_preinvoke_trigger_direction.py <probe-report.json>', file=sys.stderr)
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

invoke_line_by_port = {}
inactive_line_by_port = {}
for i, line in enumerate(lines):
    m = re.search(
        r'steelsearch_netty4tcpchannel_close_invoked channel \[\[id: .* L:/127\.0\.0\.1:(\d+) ! R:.*127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\]\] serverChannel \[(true|false)\] closeInvokeOrder \[(\d+)\]',
        line,
    )
    if m:
        invoke_line_by_port.setdefault(m.group(1), i)
    m = re.search(
        r'netty4 message channel handler channelInactive on \[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), remoteAddress=.*127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\}\]',
        line,
    )
    if m:
        inactive_line_by_port.setdefault(m.group(1), i)

first_trigger_by_conn = {}
for i, line in enumerate(lines):
    m = re.search(
        r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\] channel '
        r'\[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), remoteAddress=.*127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\}\]',
        line,
    )
    if not m or '{rust-replica-1}' not in line:
        continue
    conn = int(m.group(1))
    idx = int(m.group(2))
    local_port = m.group(3)
    invoke_line = invoke_line_by_port.get(local_port)
    if invoke_line is None or invoke_line > i:
        first_trigger_by_conn.setdefault(
            conn,
            {
                'conn': conn,
                'idx': idx,
                'family': family_for_index(idx),
                'local_port': local_port,
                'observed_line': i,
                'invoke_line': invoke_line,
                'inactive_line': inactive_line_by_port.get(local_port),
            },
        )

direction_counts = Counter()
family_direction_counts = Counter()
sample = []
for row in first_trigger_by_conn.values():
    inactive_line = row['inactive_line']
    invoke_line = row['invoke_line']
    if inactive_line is not None and (invoke_line is None or inactive_line < invoke_line):
        direction = 'channelInactive_before_invoke'
    elif invoke_line is None:
        direction = 'no_invoke_seen'
    else:
        direction = 'invoke_before_or_without_channelInactive'
    direction_counts[direction] += 1
    family_direction_counts[f"{row['family']}|{direction}"] += 1
    if len(sample) < 5:
        enriched = dict(row)
        enriched['direction'] = direction
        sample.append(enriched)

print(f'failure_port={failure_port}')
print(f'trigger_row_count={len(first_trigger_by_conn)}')
print(f'direction_counts={dict(direction_counts)}')
print(f'family_direction_counts={dict(family_direction_counts)}')
print(f'sample={sample}')

if direction_counts['channelInactive_before_invoke'] >= max(1, len(first_trigger_by_conn) - 5):
    print('result=preinvoke_low_index_trigger_best_matches_remote_side_close_or_channelinactive_before_local_fanout')
elif direction_counts['invoke_before_or_without_channelInactive'] >= max(1, len(first_trigger_by_conn) - 5):
    print('result=preinvoke_low_index_trigger_points_away_from_remote_channelinactive_and_toward_late_surfacing_local_explicit_close_residue')
else:
    print('result=preinvoke_low_index_trigger_direction_remains_mixed_or_inconclusive')
