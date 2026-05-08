#!/usr/bin/env python3
import json
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_rust_pre_first_frame_endings_point_away_from_rust_fin.py <transport-seed-capture.json>', file=sys.stderr)
    sys.exit(2)

capture = json.loads(Path(sys.argv[1]).read_text())
pre = [item for item in capture if item.get('first_frame', {}).get('pre_first_frame')]
end_counts = {}
post_counts = {}
for item in pre:
    end = item.get('connection_end')
    post = item.get('first_post_response_event')
    end_counts[end] = end_counts.get(end, 0) + 1
    post_counts[post] = post_counts.get(post, 0) + 1

idle_timeout = end_counts.get('idle_timeout', 0)
remote_eof = end_counts.get('remote_eof', 0)
result = 'undetermined'
if pre and idle_timeout > remote_eof:
    result = 'rust_pre_first_frame_endings_point_away_from_rust_active_fin_and_toward_request_missing_idle_lifecycle'

print(f'pre_first_frame_count={len(pre)}')
print(f'end_counts={end_counts}')
print(f'post_counts={post_counts}')
print(f'result={result}')
