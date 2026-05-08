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
    print('usage: check_initial_close_skew_points_away_from_caller_selection_bias.py <probe-report.json>', file=sys.stderr)
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
        first_close_by_conn.setdefault(conn, (idx, local_port))

caller6_by_port = {}
for line in lines:
    m = re.search(
        r'steelsearch_netty4tcpchannel_close_caller channel \[\[id: .* L:/127\.0\.0\.1:(\d+) ! R:.*127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\]\] serverChannel \[(true|false)\] caller \[(.+?)\] callerParent \[(.+?)\] callerGrandparent \[(.+?)\] callerGreatGrandparent \[(.+?)\] callerGreatGreatGrandparent \[(.+?)\] callerGreatGreatGreatGrandparent \[(.+)\]',
        line,
    )
    if m:
        caller6_by_port.setdefault(m.group(1), m.group(8))

family_counts = Counter()
caller6_counts = Counter()
family_caller6_counts = Counter()
matched = 0
missing = 0
sample = []

for conn, (idx, local_port) in sorted(first_close_by_conn.items()):
    family = family_for_index(idx)
    family_counts[family] += 1
    caller6 = caller6_by_port.get(local_port)
    if caller6 is None:
        missing += 1
        continue
    matched += 1
    caller6_counts[caller6] += 1
    family_caller6_counts[f'{family}|{caller6}'] += 1
    if len(sample) < 5:
        sample.append({'conn': conn, 'idx': idx, 'family': family, 'local_port': local_port, 'caller6': caller6})

print(f'failure_port={failure_port}')
print(f'named_connection_count={len(first_close_by_conn)}')
print(f'matched_caller6_count={matched}')
print(f'missing_caller6_count={missing}')
print(f'first_close_family_counts={dict(family_counts)}')
print(f'caller6_counts={dict(caller6_counts)}')
print(f'family_caller6_counts={dict(family_caller6_counts)}')
print(f'sample={sample}')

dominant_caller6 = 'org.opensearch.transport.TcpTransport$ChannelsConnectedListener#lambda$onResponse$0:1123'
low_index_total = family_counts['BULK'] + family_counts['RECOVERY']
low_index_same_caller = sum(
    count
    for key, count in family_caller6_counts.items()
    if key.startswith('BULK|' + dominant_caller6) or key.startswith('RECOVERY|' + dominant_caller6)
)
if low_index_total >= 1 and low_index_same_caller >= max(1, low_index_total - 5):
    print('result=initial_close_skew_points_away_from_distinct_caller_selection_bias_and_toward_common_fanout_ordering_state')
else:
    print('result=initial_close_skew_could_still_reflect_mixed_callers_or_selection_bias')
