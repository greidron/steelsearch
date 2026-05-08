#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

if len(sys.argv) != 3:
    print('usage: check_publish_state_transport_failure_matches_explicit_local_close.py <probe-report.json> <TcpTransport.java>', file=sys.stderr)
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
stdout_log = Path(report['work_dir']) / 'opensearch' / 'stdout.log'
text = stdout_log.read_text(errors='ignore') if stdout_log.exists() else ''
tcp_transport = Path(sys.argv[2]).read_text()

failure_ports = re.findall(
    r'steelsearch_publication_response_class=transport_failure discoveryNode=\{[^}]*\}\{[^}]*\}\{[^}]*\}\{[^}]*\}\{127\.0\.0\.1:(\d+)\}',
    text,
)
explicit_ports = re.findall(r'netty4 tcp channel close completed .* R:/127\.0\.0\.1:(\d+)\]\] with hint \[explicitLocalClose\]', text)

failure_counter = Counter(failure_ports)
explicit_counter = Counter(explicit_ports)
shared_ports = sorted(set(failure_counter) & set(explicit_counter))

counts = {
    'publication_transport_failure': len(re.findall(r'steelsearch_publication_response_class=transport_failure', text)),
    'publish_state_nodedisconnected': len(re.findall(r'NodeDisconnectedException .*\[internal:cluster/coordination/publish_state\] disconnected', text)),
    'explicit_local_close_all': len(re.findall(r'hint \[explicitLocalClose\]', text)),
    'shared_failure_and_explicit_port_count': len(shared_ports),
    'source_any_channel_close_listener_owns_nodechannels': int('channel.addCloseListener' in tcp_transport and 'nodeChannels.close();' in tcp_transport),
}
for k, v in counts.items():
    print(f'{k}={v}')
print(f'failure_ports_top={failure_counter.most_common(5)}')
print(f'explicit_ports_top={explicit_counter.most_common(5)}')
print(f'shared_ports={shared_ports[:10]}')
print(f'failure_stage={report.get("failure_stage")}')
print(f'blocker_class={report.get("blocker_class")}')

if counts['publication_transport_failure'] > 0 and counts['publish_state_nodedisconnected'] > 0 and counts['explicit_local_close_all'] > 0 and counts['shared_failure_and_explicit_port_count'] > 0 and counts['source_any_channel_close_listener_owns_nodechannels'] == 1:
    print('result=publish_state_transport_failure_matches_java_client_side_explicit_local_close_teardown_path')
else:
    print('result=publish_state_transport_failure_not_yet_linked_to_explicit_local_close_path')
