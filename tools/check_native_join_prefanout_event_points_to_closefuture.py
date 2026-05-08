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
for i,line in enumerate(lines):
    if 'node connection [2] observed close on channelIndex' in line and f':{rust_port}' in line and 'rust-replica-1' in line:
        first_idx = i
        break
window = lines[first_idx:first_idx+25] if first_idx is not None else []
closefuture = sum(1 for line in window if 'with hint [closeFutureIntercepted]' in line and f':{rust_port}' in line)
explicit = sum(1 for line in window if 'with hint [explicitLocalClose]' in line and f':{rust_port}' in line)
invoked = sum(1 for line in window if 'steelsearch_netty4tcpchannel_close_invoked' in line and f':{rust_port}' in line)
summary = {
    'rust_port': rust_port,
    'window_closefutureintercepted_count': closefuture,
    'window_explicitlocalclose_count': explicit,
    'window_close_invoked_count': invoked,
}
summary['result'] = 'native_join_prefanout_event_points_to_preclosed_closefuture_sibling' if (closefuture > 0 and invoked > 0) else 'inconclusive'
print(json.dumps(summary, indent=2))
