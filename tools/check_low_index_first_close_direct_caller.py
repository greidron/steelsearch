#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_low_index_first_close_direct_caller.py <probe-report.json>', file=sys.stderr)
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

first_low_by_conn = {}
for i, line in enumerate(lines):
    m = re.search(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\] channel \[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), remoteAddress=.*127\.0\.0\.1:' + re.escape(failure_port) + r'\}\]', line)
    if m and '{rust-replica-1}' in line:
        conn = int(m.group(1))
        idx = int(m.group(2))
        local_port = m.group(3)
        if idx in (1, 2, 5, 6) and conn not in first_low_by_conn:
            first_low_by_conn[conn] = (local_port, idx, i)

caller_by_port = {}
for i, line in enumerate(lines):
    m = re.search(
        r'steelsearch_netty4tcpchannel_close_caller channel \[\[id: .* L:/127\.0\.0\.1:(\d+) ! R:.*127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\]\] serverChannel \[(true|false)\] caller \[(.+?)\] callerParent \[(.+?)\] callerGrandparent \[(.+?)\] callerGreatGrandparent \[(.+?)\] callerGreatGreatGrandparent \[(.+?)\] callerGreatGreatGreatGrandparent \[(.+)\]',
        line,
    )
    if m:
        caller_by_port.setdefault(m.group(1), []).append((i, m.group(2), m.group(3), m.group(4), m.group(5), m.group(6), m.group(7), m.group(8)))
    m = re.search(
        r'steelsearch_netty4tcpchannel_close_caller channel \[\[id: .* L:null ! R:/127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\]\] serverChannel \[(true|false)\] caller \[(.+?)\] callerParent \[(.+?)\] callerGrandparent \[(.+?)\] callerGreatGrandparent \[(.+?)\] callerGreatGreatGrandparent \[(.+?)\] callerGreatGreatGreatGrandparent \[(.+)\]',
        line,
    )
    if m:
        caller_by_port.setdefault('null', []).append((i, m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6), m.group(7)))

caller_counter = Counter()
caller_parent_counter = Counter()
caller_grandparent_counter = Counter()
caller_great_grandparent_counter = Counter()
caller_great_great_grandparent_counter = Counter()
caller_great_great_great_grandparent_counter = Counter()
missing = 0
sample = []
for conn, (local_port, idx, close_i) in sorted(first_low_by_conn.items()):
    matches = caller_by_port.get(local_port, [])
    if not matches:
        missing += 1
        continue
    caller = matches[0][2]
    caller_parent = matches[0][3]
    caller_grandparent = matches[0][4]
    caller_great_grandparent = matches[0][5]
    caller_great_great_grandparent = matches[0][6]
    caller_great_great_great_grandparent = matches[0][7]
    caller_counter[caller] += 1
    caller_parent_counter[caller_parent] += 1
    caller_grandparent_counter[caller_grandparent] += 1
    caller_great_grandparent_counter[caller_great_grandparent] += 1
    caller_great_great_grandparent_counter[caller_great_great_grandparent] += 1
    caller_great_great_great_grandparent_counter[caller_great_great_great_grandparent] += 1
    if len(sample) < 5:
        sample.append(
            {
                'conn': conn,
                'idx': idx,
                'local_port': local_port,
                'caller': caller,
                'caller_parent': caller_parent,
                'caller_grandparent': caller_grandparent,
                'caller_great_grandparent': caller_great_grandparent,
                'caller_great_great_grandparent': caller_great_great_grandparent,
                'caller_great_great_great_grandparent': caller_great_great_great_grandparent,
            }
        )

print(f'failure_port={failure_port}')
print(f'first_low_connection_count={len(first_low_by_conn)}')
print(f'matched_caller_count={sum(caller_counter.values())}')
print(f'missing_caller_count={missing}')
print(f'caller_counts={dict(caller_counter)}')
print(f'caller_parent_counts={dict(caller_parent_counter)}')
print(f'caller_grandparent_counts={dict(caller_grandparent_counter)}')
print(f'caller_great_grandparent_counts={dict(caller_great_grandparent_counter)}')
print(f'caller_great_great_grandparent_counts={dict(caller_great_great_grandparent_counter)}')
print(f'caller_great_great_great_grandparent_counts={dict(caller_great_great_great_grandparent_counter)}')
print(f'sample={sample}')
if (
    len(caller_counter) == 1
    and len(caller_parent_counter) == 1
    and len(caller_grandparent_counter) == 1
    and len(caller_great_grandparent_counter) == 1
    and len(caller_great_great_grandparent_counter) == 1
    and len(caller_great_great_great_grandparent_counter) == 1
    and sum(caller_counter.values()) >= max(1, len(first_low_by_conn) - 10)
):
    print('result=low_index_first_close_direct_caller_stack_is_dominated_by_single_frames')
elif len(caller_counter) == 1 and len(caller_parent_counter) == 1 and sum(caller_counter.values()) >= max(1, len(first_low_by_conn) - 8):
    print('result=low_index_first_close_direct_caller_and_parent_are_dominated_by_single_frames')
elif len(caller_counter) == 1 and sum(caller_counter.values()) >= max(1, len(first_low_by_conn) - 8):
    print('result=low_index_first_close_direct_caller_is_dominated_by_a_single_caller')
elif len(caller_counter) == 1 and sum(caller_counter.values()) == len(first_low_by_conn):
    print('result=low_index_first_close_direct_caller_is_uniquely_identified')
else:
    print('result=low_index_first_close_direct_caller_is_mixed_or_incomplete')
