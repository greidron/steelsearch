#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from statistics import median

if len(sys.argv) != 4:
    print(
        'usage: check_publication_disconnect_tracks_connection_close_callback_not_active_state_traffic.py '
        '<probe-report.json> <TcpTransport.java> <TransportService.java>',
        file=sys.stderr,
    )
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
tcptransport = Path(sys.argv[2]).read_text()
transportservice = Path(sys.argv[3]).read_text()
stdout_log = Path(report['work_dir']) / 'opensearch' / 'stdout.log'
lines = stdout_log.read_text(errors='ignore').splitlines()

failure_rows = []
failure_port = None
for i, line in enumerate(lines):
    if 'steelsearch_publication_response_class=transport_failure' not in line:
        continue
    m = re.search(r'\{127\.0\.0\.1:(\d+)\}', line)
    if not m:
        continue
    port = m.group(1)
    if failure_port is None:
        failure_port = port
    if port == failure_port:
        failure_rows.append(i)

if not failure_rows:
    print('failure_row_count=0')
    print('result=missing_publication_transport_failure_rows')
    sys.exit(1)

closed_conn_gaps = []
state_close_gaps = []
reg_close_gaps = []
followers_disconnected_gaps = []
for failure_i in failure_rows:
    prev_closed_conn = None
    prev_state_close = None
    prev_reg_close = None
    prev_followers_disconnected = None
    for j in range(failure_i - 1, -1, -1):
        line = lines[j]
        if f'127.0.0.1:{failure_port}' not in line:
            continue
        if prev_closed_conn is None and 'closed transport connection [' in line and '{rust-replica-1}' in line:
            prev_closed_conn = failure_i - j
        if prev_state_close is None and 'node connection [' in line and 'channelIndex [4]' in line and '{rust-replica-1}' in line:
            prev_state_close = failure_i - j
        if prev_reg_close is None and 'node connection [' in line and '{rust-replica-1}' in line:
            m_idx = re.search(r'channelIndex \[(\d+)\]', line)
            if m_idx and 7 <= int(m_idx.group(1)) <= 12:
                prev_reg_close = failure_i - j
        if prev_followers_disconnected is None and 'FollowersChecker' in line and 'disconnected' in line:
            prev_followers_disconnected = failure_i - j
        if prev_closed_conn and prev_state_close and prev_reg_close and prev_followers_disconnected:
            break
    if prev_closed_conn is not None:
        closed_conn_gaps.append(prev_closed_conn)
    if prev_state_close is not None:
        state_close_gaps.append(prev_state_close)
    if prev_reg_close is not None:
        reg_close_gaps.append(prev_reg_close)
    if prev_followers_disconnected is not None:
        followers_disconnected_gaps.append(prev_followers_disconnected)

print(f'failure_port={failure_port}')
print(f'failure_row_count={len(failure_rows)}')
print(f'source_any_sibling_close_calls_nodechannels_close={"nodeChannels.close();" in tcptransport}')
print(f'source_transportservice_prunes_handlers_on_connection_close={"responseHandlers.prune" in transportservice and "NodeDisconnectedException" in transportservice}')
print(
    'closed_transport_connection_to_failure_lines='
    + str({'min': min(closed_conn_gaps), 'median': median(closed_conn_gaps), 'max': max(closed_conn_gaps)})
)
print(
    'followers_disconnected_to_failure_lines='
    + str({'min': min(followers_disconnected_gaps), 'median': median(followers_disconnected_gaps), 'max': max(followers_disconnected_gaps)})
)
print(
    'state_close_to_failure_lines='
    + str({'min': min(state_close_gaps), 'median': median(state_close_gaps), 'max': max(state_close_gaps)})
)
print(
    'reg_close_to_failure_lines='
    + str({'min': min(reg_close_gaps), 'median': median(reg_close_gaps), 'max': max(reg_close_gaps)})
)

if (
    'nodeChannels.close();' in tcptransport
    and 'responseHandlers.prune' in transportservice
    and 'NodeDisconnectedException' in transportservice
    and median(closed_conn_gaps) < median(state_close_gaps)
):
    print('result=publication_disconnect_tracks_connection_close_callback_chain_more_than_active_state_or_reg_traffic')
else:
    print('result=publication_disconnect_cause_still_ambiguous_between_callback_chain_and_active_traffic')
