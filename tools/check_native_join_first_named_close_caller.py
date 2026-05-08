#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
rust_port = None
for line in lines:
    m = re.search(r'rootCauseMessage=\[rust-replica-1\]\[127\.0\.0\.1:(\d+)\]\[internal:cluster/coordination/publish_state\] disconnected', line)
    if m:
        rust_port = m.group(1)
        break
first_idx = None
first_line = None
local_addr = None
for i,line in enumerate(lines):
    if 'node connection [' in line and 'observed close on channelIndex' in line and 'rust-replica-1' in line and f':{rust_port}' in line:
        first_idx = i
        first_line = line
        m = re.search(r'localAddress=/127\.0\.0\.1:(\d+), remoteAddress=.*:(\d+)\}', line)
        if m:
            local_addr = m.group(1)
        break
matching_caller = None
if first_idx is not None:
    for j in range(max(0, first_idx - 20), min(len(lines), first_idx + 40)):
        line = lines[j]
        if 'steelsearch_netty4tcpchannel_close_caller' not in line:
            continue
        if local_addr and f'L:/127.0.0.1:{local_addr}' not in line:
            continue
        matching_caller = line
        break
summary = {
    'rust_port': rust_port,
    'first_named_close_line': first_line,
    'matching_caller_line': matching_caller,
}
summary['result'] = 'native_join_first_named_close_caller_is_channelsconnectedlistener_fanout' if (
    matching_caller is not None and 'TcpTransport$ChannelsConnectedListener#lambda$onResponse$0:1123' in matching_caller
) else 'inconclusive'
print(json.dumps(summary, indent=2))
