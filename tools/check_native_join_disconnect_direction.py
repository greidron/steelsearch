#!/usr/bin/env python3
import json
import sys
from pathlib import Path

obj = json.loads(Path(sys.argv[1]).read_text())
cap = obj.get('steelsearch_transport_capture') or []
publish_rows = []
for row in cap:
    actions = [
        (row.get('first_frame') or {}).get('action_hint'),
        (row.get('follow_up_frame') or {}).get('action_hint'),
        (row.get('post_follow_up_frame') or {}).get('action_hint'),
    ]
    if 'internal:cluster/coordination/publish_state' in actions:
        publish_rows.append(row)

stdout = Path(obj['artifacts']['opensearch_stdout']).read_text(encoding='utf-8', errors='replace').splitlines()
publish_disconnect_count = sum(
    1 for line in stdout
    if 'rootCauseMessage=' in line and '[internal:cluster/coordination/publish_state] disconnected' in line
)
summary = {
    'publish_capture_count': len(publish_rows),
    'publish_remote_eof_count': sum(1 for row in publish_rows if row.get('connection_end') == 'remote_eof'),
    'publish_non_remote_eof_count': sum(1 for row in publish_rows if row.get('connection_end') != 'remote_eof'),
    'publish_disconnect_log_count': publish_disconnect_count,
}
summary['result'] = 'native_join_disconnect_points_away_from_rust_active_close' if (
    summary['publish_capture_count'] > 0
    and summary['publish_remote_eof_count'] == summary['publish_capture_count']
    and summary['publish_disconnect_log_count'] > 0
) else 'inconclusive'
print(json.dumps(summary, indent=2))
