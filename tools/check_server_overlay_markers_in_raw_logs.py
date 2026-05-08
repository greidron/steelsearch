#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_server_overlay_markers_in_raw_logs.py <probe-report.json>', file=sys.stderr)
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
work_dir = Path(report['work_dir'])
stdout_log = work_dir / 'opensearch' / 'stdout.log'
if not stdout_log.exists():
    print(f'stdout_log_exists=false')
    print(f'stdout_log_path={stdout_log}')
    print('result=missing_opensearch_stdout_log')
    sys.exit(1)
text = stdout_log.read_text(errors='ignore')
patterns = {
    'class_load_coordination': r'steelsearch_class_load_marker=CoordinationState',
    'class_load_publication': r'steelsearch_class_load_marker=Publication',
    'publication_onresponse_entry': r'steelsearch_publication_onResponse_entry',
    'handlejoin_entry': r'steelsearch_handleJoin_entry',
    'publication_transport_failure': r'steelsearch_publication_response_class=transport_failure',
    'node_disconnected_publish_state': r'NodeDisconnectedException .*\[internal:cluster/coordination/publish_state\] disconnected',
}
for key, pat in patterns.items():
    print(f'{key}={len(re.findall(pat, text))}')
print(f'stdout_log_exists=true')
print(f'stdout_log_path={stdout_log}')
if re.search(patterns['publication_transport_failure'], text):
    print('result=server_overlay_is_applied_and_raw_logs_surface_publish_state_transport_failure')
else:
    print('result=server_overlay_markers_not_found_in_raw_logs')
