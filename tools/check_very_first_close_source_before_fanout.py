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
    print('usage: check_very_first_close_source_before_fanout.py <probe-report.json>', file=sys.stderr)
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

invoke_line_by_local_port = {}
hint_by_local_port = {}
for i, line in enumerate(lines):
    m = re.search(
        r'steelsearch_netty4tcpchannel_close_invoked channel \[\[id: .* L:/127\.0\.0\.1:(\d+) ! R:.*127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\]\] serverChannel \[(true|false)\] closeInvokeOrder \[(\d+)\]',
        line,
    )
    if m:
        invoke_line_by_local_port.setdefault(m.group(1), i)
    m = re.search(
        r'netty4 tcp channel close completed for \[\[id: .* L:/127\.0\.0\.1:(\d+) ! R:.*127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\]\] with hint \[(.+?)\]',
        line,
    )
    if m:
        hint_by_local_port.setdefault(m.group(1), m.group(2))

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
    invoke_line = invoke_line_by_local_port.get(local_port)
    if invoke_line is None or invoke_line > i:
        first_trigger_by_conn.setdefault(conn, (idx, local_port, i, invoke_line))

family_counts = Counter()
index_counts = Counter()
hint_counts = Counter()
sample = []

for conn, (idx, local_port, line_no, invoke_line) in sorted(first_trigger_by_conn.items()):
    family = family_for_index(idx)
    family_counts[family] += 1
    index_counts[idx] += 1
    hint_counts[hint_by_local_port.get(local_port, 'missing')] += 1
    if len(sample) < 5:
        sample.append(
            {
                'conn': conn,
                'idx': idx,
                'family': family,
                'local_port': local_port,
                'invoke_line': invoke_line,
                'hint': hint_by_local_port.get(local_port, 'missing'),
            }
        )

print(f'failure_port={failure_port}')
print(f'trigger_connection_count={len(first_trigger_by_conn)}')
print(f'trigger_family_counts={dict(family_counts)}')
print(f'trigger_index_counts={dict(index_counts)}')
print(f'trigger_hint_counts={dict(hint_counts)}')
print(f'sample={sample}')

dominant_family = family_counts.most_common(1)[0][0] if family_counts else 'none'
if dominant_family in {'BULK', 'RECOVERY'}:
    print('result=very_first_close_source_before_fanout_is_dominated_by_low_index_non_action_family')
else:
    print('result=very_first_close_source_before_fanout_is_not_dominated_by_low_index_non_action_family')
