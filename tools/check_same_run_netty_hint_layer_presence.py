#!/usr/bin/env python3
import json
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_same_run_netty_hint_layer_presence.py <probe-report.json>', file=sys.stderr)
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
stdout_log = Path(report['work_dir']) / 'opensearch' / 'stdout.log'
stderr_log = Path(report['work_dir']) / 'opensearch' / 'stderr.log'
out = stdout_log.read_text(errors='ignore') if stdout_log.exists() else ''
err = stderr_log.read_text(errors='ignore') if stderr_log.exists() else ''
counts = {
    'stderr_netty4_logger_echo': err.count('OpenSearch Netty4TcpChannel log level: TRACE'),
    'stderr_extra_overlay_echo': err.count('OpenSearch extra jar overlay specs:'),
    'stdout_netty_close_completed': out.count('netty4 tcp channel close completed'),
    'stdout_hint_explicit': out.count('hint[explicitLocalClose]'),
    'stdout_hint_unknown': out.count('hint[unknown]'),
    'stdout_channelinactive': out.count('Netty4MessageChannelHandler.channelInactive'),
    'stdout_publication_transport_failure': out.count('steelsearch_publication_response_class=transport_failure'),
}
for k,v in counts.items():
    print(f'{k}={v}')
if counts['stderr_netty4_logger_echo'] > 0 and counts['stderr_extra_overlay_echo'] > 0 and counts['stdout_netty_close_completed'] == 0 and counts['stdout_publication_transport_failure'] > 0:
    print('result=same_run_disconnect_surfaces_above_publication_but_netty_hint_layer_is_missing_in_runtime_logs')
else:
    print('result=same_run_netty_hint_layer_presence_not_yet_classified')
