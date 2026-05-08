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
    print('usage: check_initial_named_sibling_close_event.py <probe-report.json>', file=sys.stderr)
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

first_close_by_conn = {}
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
        first_close_by_conn.setdefault(conn, (i, idx, local_port))

hint_by_local_port = {}
for i, line in enumerate(lines):
    m = re.search(
        r'netty4 tcp channel close completed for \[\[id: .* L:/127\.0\.0\.1:(\d+) ! R:.*127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\]\] with hint \[(.+?)\]',
        line,
    )
    if m:
        hint_by_local_port.setdefault(m.group(1), (i, m.group(2)))

family_counts = Counter()
index_counts = Counter()
hint_counts = Counter()
sample = []
missing_hint = 0

for conn, (line_no, idx, local_port) in sorted(first_close_by_conn.items()):
    family = family_for_index(idx)
    family_counts[family] += 1
    index_counts[idx] += 1
    hint = 'missing'
    if local_port in hint_by_local_port:
        hint = hint_by_local_port[local_port][1]
        hint_counts[hint] += 1
    else:
        missing_hint += 1
    if len(sample) < 5:
        sample.append(
            {
                'conn': conn,
                'idx': idx,
                'family': family,
                'local_port': local_port,
                'hint': hint,
            }
        )

print(f'failure_port={failure_port}')
print(f'named_connection_count={len(first_close_by_conn)}')
print(f'first_close_family_counts={dict(family_counts)}')
print(f'first_close_index_counts={dict(index_counts)}')
print(f'first_close_hint_counts={dict(hint_counts)}')
print(f'missing_hint_count={missing_hint}')
print(f'sample={sample}')

dominant_family = family_counts.most_common(1)[0][0] if family_counts else 'none'
dominant_hint = hint_counts.most_common(1)[0][0] if hint_counts else 'none'
if dominant_hint == 'explicitLocalClose' and dominant_family in {'BULK', 'RECOVERY'}:
    print('result=initial_named_sibling_close_event_is_dominated_by_low_index_local_explicit_close')
elif dominant_family in {'BULK', 'RECOVERY'}:
    print('result=initial_named_sibling_close_event_is_dominated_by_low_index_family_but_hint_is_mixed')
else:
    print('result=initial_named_sibling_close_event_is_not_dominated_by_low_index_local_explicit_close')
