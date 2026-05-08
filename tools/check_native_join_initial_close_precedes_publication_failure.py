#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
rust_port = None
for line in lines:
    m = re.search(r'rootCauseMessage=\[rust-replica-1\]\[127\.0\.0\.1:(\d+)\]\[internal:cluster/coordination/publish_state\] disconnected', line)
    if m:
        rust_port = m.group(1)
        break

first_named_ts = None
first_named_line = None
for line in lines:
    if 'node connection [' in line and 'observed close on channelIndex' in line and 'rust-replica-1' in line and f':{rust_port}' in line:
        ts = datetime.fromisoformat(line[1:24])
        if first_named_ts is None or ts < first_named_ts:
            first_named_ts = ts
            first_named_line = line

first_pubfail_ts = None
first_pubfail_line = None
for line in lines:
    if 'steelsearch_publication_response_class=transport_failure' in line and f':{rust_port}' in line:
        ts = datetime.fromisoformat(line[1:24])
        if first_pubfail_ts is None or ts < first_pubfail_ts:
            first_pubfail_ts = ts
            first_pubfail_line = line

summary = {
    'rust_port': rust_port,
    'first_named_close_line': first_named_line,
    'first_publication_failure_line': first_pubfail_line,
    'first_named_precedes_publication_failure': bool(first_named_ts and first_pubfail_ts and first_named_ts < first_pubfail_ts),
}
summary['result'] = 'native_join_initial_close_points_away_from_publish_state_callback_close' if summary['first_named_precedes_publication_failure'] else 'inconclusive'
print(json.dumps(summary, indent=2))
