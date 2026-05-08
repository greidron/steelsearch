#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

if len(sys.argv) != 4:
    print(
        'usage: check_low_index_explicitlocalclose_points_away_from_keepalive.py '
        '<probe-report.json> <TransportKeepAlive.java> <Netty4TcpChannel.java>',
        file=sys.stderr,
    )
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
keepalive = Path(sys.argv[2]).read_text()
netty4tcp = Path(sys.argv[3]).read_text()
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

named_conn_count = 0
probe_before_first = 0
for i, line in enumerate(lines):
    m = re.search(r'opened transport connection \[(\d+)\] to \[(.+)\] using channels', line)
    if not m or f'127.0.0.1:{failure_port}' not in line or not m.group(2).startswith('{rust-replica-1}'):
        continue
    named_conn_count += 1
    first_low = None
    next_probe = None
    for j in range(i + 1, len(lines)):
        row = lines[j]
        if f'127.0.0.1:{failure_port}' not in row:
            continue
        if next_probe is None and 'opened transport connection [' in row and f'to [{{127.0.0.1:{failure_port}}}' in row:
            next_probe = j
        if first_low is None and 'node connection [' in row and '{rust-replica-1}' in row:
            m_idx = re.search(r'channelIndex \[(\d+)\]', row)
            if m_idx and int(m_idx.group(1)) in (1, 2, 5, 6):
                first_low = j
                break
    if first_low is not None and next_probe is not None and next_probe < first_low:
        probe_before_first += 1

print(f'failure_port={failure_port}')
print(f'named_connection_count={named_conn_count}')
print(f'probe_before_first_low_close_count={probe_before_first}')
print(f'source_keepalive_registers_only={"scheduledPing.addChannel(channel)" in keepalive}')
print(f'source_keepalive_sends_ping={"sendPing(channel)" in keepalive}')
print(f'source_keepalive_has_no_channel_close_call={"channel.close()" not in keepalive and ".close();" not in keepalive}')
print(f'source_explicit_local_close_lives_in_netty4tcpchannel_close={"recordCloseHint(\"explicitLocalClose\", null)" in netty4tcp and "channel.close();" in netty4tcp}')

if (
    probe_before_first == 0
    and 'scheduledPing.addChannel(channel)' in keepalive
    and 'sendPing(channel)' in keepalive
    and 'channel.close()' not in keepalive
    and '.close();' not in keepalive
    and 'recordCloseHint("explicitLocalClose", null)' in netty4tcp
):
    print('result=low_index_explicitlocalclose_points_away_from_keepalive_idle_cleanup_and_toward_a_direct_channel_close_path')
else:
    print('result=low_index_explicitlocalclose_caller_still_ambiguous_between_keepalive_and_direct_close')
