#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_publish_state_disconnect_direction.py <probe-report.json>', file=sys.stderr)
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
transport_rows = report['steelsearch_transport_capture']
publish_rows = []
for row in transport_rows:
    frames = [row.get('first_frame') or {}, row.get('follow_up_frame') or {}, row.get('post_follow_up_frame') or {}]
    actions = [f.get('action_hint') for f in frames]
    if 'internal:cluster/coordination/publish_state' in actions:
        publish_rows.append(row)

stdout_log = Path(report['work_dir']) / 'opensearch' / 'stdout.log'
text = stdout_log.read_text(errors='ignore') if stdout_log.exists() else ''
java_publish_disconnects = len(re.findall(r'NodeDisconnectedException .*\[internal:cluster/coordination/publish_state\] disconnected', text))

rust_remote_eof = sum(1 for row in publish_rows if row.get('connection_end') == 'remote_eof')
rust_non_remote = sum(1 for row in publish_rows if row.get('connection_end') != 'remote_eof')

print(f'publish_row_count={len(publish_rows)}')
print(f'rust_publish_remote_eof_count={rust_remote_eof}')
print(f'rust_publish_non_remote_eof_count={rust_non_remote}')
print(f'java_publish_state_nodedisconnected_count={java_publish_disconnects}')

if publish_rows:
    sample = publish_rows[0]
    print(f"sample_first_action={(sample.get('first_frame') or {}).get('action_hint')}")
    print(f"sample_connection_end={sample.get('connection_end')}")
    print(f"sample_first_post_response_event={sample.get('first_post_response_event')}")

if rust_remote_eof > 0 and java_publish_disconnects > 0 and rust_non_remote == 0:
    print('result=publish_state_disconnect_direction_points_away_from_rust_active_close_and_toward_java_side_disconnect')
else:
    print('result=publish_state_disconnect_direction_is_not_yet_fixed')
