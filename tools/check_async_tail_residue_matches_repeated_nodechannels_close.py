#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path


if len(sys.argv) != 2:
    print('usage: check_async_tail_residue_matches_repeated_nodechannels_close.py <probe-report.json>', file=sys.stderr)
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

invoke_by_port = {}
caller6_by_port = {}
for i, line in enumerate(lines):
    m = re.search(
        r'steelsearch_netty4tcpchannel_close_invoked channel \[\[id: .* L:/127\.0\.0\.1:(\d+) ! R:.*127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\]\] serverChannel \[(true|false)\] closeInvokeOrder \[(\d+)\]',
        line,
    )
    if m:
        invoke_by_port.setdefault(m.group(1), i)
    m = re.search(
        r'steelsearch_netty4tcpchannel_close_caller channel \[\[id: .* L:/127\.0\.0\.1:(\d+) ! R:.*127\.0\.0\.1:'
        + re.escape(failure_port)
        + r'\]\] serverChannel \[(true|false)\] caller \[(.+?)\] callerParent \[(.+?)\] callerGrandparent \[(.+?)\] callerGreatGrandparent \[(.+?)\] callerGreatGreatGrandparent \[(.+?)\] callerGreatGreatGreatGrandparent \[(.+)\]',
        line,
    )
    if m:
        caller6_by_port.setdefault(m.group(1), m.group(8))

first_trigger_rows = {}
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
    invoke_line = invoke_by_port.get(local_port)
    if invoke_line is None or invoke_line > i:
        first_trigger_rows.setdefault(conn, (idx, local_port, i, invoke_line))

caller6_counts = Counter()
sample = []
matched = 0
for conn, (idx, local_port, observed_line, invoke_line) in sorted(first_trigger_rows.items()):
    caller6 = caller6_by_port.get(local_port, 'missing')
    caller6_counts[caller6] += 1
    if caller6 != 'missing':
        matched += 1
    if len(sample) < 5:
        sample.append(
            {
                'conn': conn,
                'idx': idx,
                'local_port': local_port,
                'observed_line': observed_line,
                'invoke_line': invoke_line,
                'caller6': caller6,
            }
        )

dominant = 'org.opensearch.transport.TcpTransport$ChannelsConnectedListener#lambda$onResponse$0:1123'
print(f'failure_port={failure_port}')
print(f'trigger_count={len(first_trigger_rows)}')
print(f'matched_caller6_count={matched}')
print(f'caller6_counts={dict(caller6_counts)}')
print(f'sample={sample}')

if caller6_counts.get(dominant, 0) >= max(1, len(first_trigger_rows) - 5):
    print('result=async_tail_residue_best_matches_repeated_nodechannels_close_pass_duplicate_local_close')
else:
    print('result=async_tail_residue_caller_chain_remains_mixed_or_inconclusive')
