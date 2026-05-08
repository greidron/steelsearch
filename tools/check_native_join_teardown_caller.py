#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

arg = Path(sys.argv[1])
if arg.suffix == '.json':
    try:
        obj = json.loads(arg.read_text())
        stdout_path = Path(obj['artifacts']['opensearch_stdout'])
    except Exception:
        stdout_path = arg
else:
    stdout_path = arg

stdout = stdout_path.read_text(encoding='utf-8', errors='replace').splitlines()
rust_port = None
for line in stdout:
    m = re.search(r'rootCauseMessage=\[rust-replica-1\]\[127\.0\.0\.1:(\d+)\]\[internal:cluster/coordination/publish_state\] disconnected', line)
    if m:
        rust_port = m.group(1)
        break
caller_counts = Counter()
explicit_count = 0
for line in stdout:
    if rust_port and f'R:127.0.0.1/127.0.0.1:{rust_port}' in line and 'steelsearch_netty4tcpchannel_close_caller' in line:
        m = re.search(r'callerGreatGreatGreatGrandparent \[(.*?)\]', line)
        if m:
            caller_counts[m.group(1)] += 1
    if rust_port and f'R:127.0.0.1/127.0.0.1:{rust_port}' in line and 'with hint [explicitLocalClose]' in line:
        explicit_count += 1
summary = {
    'stdout_path': str(stdout_path),
    'rust_port': rust_port,
    'caller_counts': dict(caller_counts),
    'explicit_local_close_count': explicit_count,
}
dominant = caller_counts.most_common(1)[0] if caller_counts else (None, 0)
summary['result'] = 'native_join_teardown_caller_is_channelsconnectedlistener_fanout' if (
    rust_port is not None and
    explicit_count > 0 and
    dominant[0] == 'org.opensearch.transport.TcpTransport$ChannelsConnectedListener#lambda$onResponse$0:1123' and
    dominant[1] >= max(10, explicit_count // 2)
) else 'inconclusive'
print(json.dumps(summary, indent=2))
