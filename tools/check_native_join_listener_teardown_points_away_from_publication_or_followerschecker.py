#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_native_join_listener_teardown_points_away_from_publication_or_followerschecker.py <stdout.log>', file=sys.stderr)
    sys.exit(2)

lines = Path(sys.argv[1]).read_text(errors='replace').splitlines()
port = None
open_idx = None
for idx, line in enumerate(lines, start=1):
    if 'opened transport connection' in line and 'rust-replica-1' in line:
        open_idx = idx
        m = re.search(r'127\.0\.0\.1:(\d+)\}\{dimr\}', line)
        if m:
            port = m.group(1)
            break
if port is None:
    raise SystemExit('could not determine rust port')

first_close_idx = None
for idx, line in enumerate(lines, start=1):
    if f'remoteAddress=127.0.0.1/127.0.0.1:{port}' in line and 'node connection [2] observed close' in line:
        first_close_idx = idx
        break
if first_close_idx is None:
    raise SystemExit('could not find first named close')

pub_before = []
followers_after = []
for idx, line in enumerate(lines, start=1):
    if 'steelsearch_publication_onResponse_entry' in line and idx < first_close_idx:
        pub_before.append((idx, line))
    if 'FollowersChecker' in line and idx > first_close_idx and idx < first_close_idx + 80:
        followers_after.append((idx, line))

pub_rust_before = [x for x in pub_before if 'rust-replica-1' in x[1]]
pub_self_before = [x for x in pub_before if 'java-primary-1' in x[1]]

result = 'inconclusive'
if pub_self_before and not pub_rust_before and followers_after:
    result = 'native_join_listener_teardown_points_away_from_publication_response_handling_and_followerschecker_disconnect_callback_and_toward_other_connection_close_callback_chain'

print(f'rust_port = {port}')
print(f'first_named_close_line = {first_close_idx}')
print(f'publication_onresponse_before_close_count = {len(pub_before)}')
print(f'publication_onresponse_for_rust_before_close_count = {len(pub_rust_before)}')
print(f'publication_onresponse_for_self_before_close_count = {len(pub_self_before)}')
print(f'followerschecker_after_close_count = {len(followers_after)}')
print(f'result = {result}')
