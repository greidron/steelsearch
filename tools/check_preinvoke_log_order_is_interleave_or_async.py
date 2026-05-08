#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


def parse_ts(line: str) -> datetime | None:
    m = re.match(r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2},\d{3})\]', line)
    if not m:
        return None
    return datetime.strptime(m.group(1), '%Y-%m-%dT%H:%M:%S,%f')


if len(sys.argv) != 2:
    print('usage: check_preinvoke_log_order_is_interleave_or_async.py <probe-report.json>', file=sys.stderr)
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
for i, line in enumerate(lines):
    m = re.search(
        r'steelsearch_netty4tcpchannel_close_invoked channel \[\[id: .* L:/127\.0\.0\.1:(\d+) ! R:.*127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\]\] serverChannel \[(true|false)\] closeInvokeOrder \[(\d+)\]',
        line,
    )
    if m:
        invoke_line_by_port.setdefault(m.group(1), (i, line))

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
    invoke = invoke_line_by_port.get(local_port)
    if invoke is None or invoke[0] > i:
        first_trigger_by_conn.setdefault(conn, (idx, local_port, i, line, invoke))

classification = Counter()
sample = []
for conn, (idx, local_port, observed_line_no, observed_line, invoke) in first_trigger_by_conn.items():
    observed_ts = parse_ts(observed_line)
    if invoke is None:
        classification['no_invoke_line'] += 1
        continue
    invoke_line_no, invoke_line = invoke
    invoke_ts = parse_ts(invoke_line)
    if invoke_ts is not None and observed_ts is not None and invoke_ts <= observed_ts:
        bucket = 'timestamp_supports_logger_interleave'
    else:
        bucket = 'timestamp_supports_async_tail'
    classification[bucket] += 1
    if len(sample) < 5:
        sample.append(
            {
                'conn': conn,
                'idx': idx,
                'local_port': local_port,
                'observed_line': observed_line_no,
                'invoke_line': invoke_line_no,
                'observed_ts': observed_ts.isoformat() if observed_ts else None,
                'invoke_ts': invoke_ts.isoformat() if invoke_ts else None,
                'bucket': bucket,
            }
        )

print(f'failure_port={failure_port}')
print(f'trigger_count={len(first_trigger_by_conn)}')
print(f'classification={dict(classification)}')
print(f'sample={sample}')

if classification['timestamp_supports_logger_interleave'] > classification['timestamp_supports_async_tail']:
    print('result=preinvoke_residue_best_matches_same_connection_logger_interleave_more_than_true_async_delay')
elif classification['timestamp_supports_async_tail'] > classification['timestamp_supports_logger_interleave']:
    print('result=preinvoke_residue_best_matches_true_async_delay_more_than_logger_interleave')
else:
    print('result=preinvoke_residue_ordering_is_mixed')
