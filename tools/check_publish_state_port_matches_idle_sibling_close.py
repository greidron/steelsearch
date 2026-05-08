#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_publish_state_port_matches_idle_sibling_close.py <probe-report.json>', file=sys.stderr)
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
stdout_log = Path(report['work_dir']) / 'opensearch' / 'stdout.log'
text = stdout_log.read_text(errors='ignore')

failure_ports = re.findall(
    r'steelsearch_publication_response_class=transport_failure discoveryNode=\{[^}]*\}\{[^}]*\}\{[^}]*\}\{[^}]*\}\{127\.0\.0\.1:(\d+)\}',
    text,
)
if not failure_ports:
    print('failure_port_present=false')
    print('result=missing_failure_port')
    sys.exit(1)

failure_port = failure_ports[0]
first_by_conn = {}
for line in text.splitlines():
    if 'node connection [' not in line or f'127.0.0.1:{failure_port}' not in line:
        continue
    m_conn = re.search(r'node connection \[(\d+)\]', line)
    m_idx = re.search(r'channelIndex \[(\d+)\]', line)
    m_order = re.search(r'closeOrder \[(\d+)\]', line)
    if not (m_conn and m_idx and m_order):
        continue
    conn = int(m_conn.group(1))
    idx = int(m_idx.group(1))
    order = int(m_order.group(1))
    prev = first_by_conn.get(conn)
    if prev is None or order < prev[1]:
        first_by_conn[conn] = (idx, order)

first_counter = Counter(idx for idx, _ in first_by_conn.values())
idle_low = sum(first_counter[i] for i in (1,2,5,6))
state_idx = first_counter[4]
ping_idx = first_counter[3]
reg_idx = sum(first_counter[i] for i in range(7,13))

print(f'failure_port={failure_port}')
print(f'connection_count={len(first_by_conn)}')
print(f'first_index_counts={dict(sorted(first_counter.items()))}')
print(f'idle_low_first_count={idle_low}')
print(f'state_first_count={state_idx}')
print(f'ping_first_count={ping_idx}')
print(f'reg_first_count={reg_idx}')

if idle_low > state_idx and idle_low > ping_idx and idle_low > reg_idx:
    print('result=publish_state_failure_port_matches_idle_low_index_first_close_more_than_state_channel_close')
else:
    print('result=publish_state_failure_port_not_yet_classified_as_idle_sibling_or_state_close')
