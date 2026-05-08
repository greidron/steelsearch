#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 4:
    print(
        'usage: check_native_join_prefanout_closefuture_points_away_from_channelinactive.py '
        '<stdout.log> <Netty4Transport.java> <Netty4MessageChannelHandler.java>',
        file=sys.stderr,
    )
    sys.exit(2)

log_path = Path(sys.argv[1])
transport_path = Path(sys.argv[2])
handler_path = Path(sys.argv[3])
lines = log_path.read_text(errors='replace').splitlines()
transport = transport_path.read_text(errors='replace')
handler = handler_path.read_text(errors='replace')

port = None
for line in lines:
    if 'opened transport connection' in line and 'rust-replica-1' in line:
        m = re.search(r'127\.0\.0\.1:(\d+)\}\{dimr\}', line)
        if m:
            port = m.group(1)
            break
if port is None:
    raise SystemExit('could not determine rust-replica port from opened transport connection')

first_close_idx = None
for idx, line in enumerate(lines, start=1):
    if f'remoteAddress=127.0.0.1/127.0.0.1:{port}' in line and 'observed close on channelIndex' in line:
        first_close_idx = idx
        break
if first_close_idx is None:
    raise SystemExit('could not find first observed close for rust port')

window = []
for idx in range(first_close_idx, min(first_close_idx + 80, len(lines) + 1)):
    line = lines[idx - 1]
    if f'127.0.0.1:{port}' in line or 'channelInactive' in line or 'closeFutureIntercepted' in line or 'explicitLocalClose' in line:
        window.append((idx, line))

closefuture_lines = [f'{i}: {l}' for i, l in window if 'closeFutureIntercepted' in l]
channelinactive_lines = [f'{i}: {l}' for i, l in window if 'channelInactive' in l]
early_channelinactive_lines = [f'{i}: {l}' for i, l in window if 'earlyChannelInactive' in l]
explicit_lines = [f'{i}: {l}' for i, l in window if 'explicitLocalClose' in l]

result = 'inconclusive'
if closefuture_lines and not channelinactive_lines and not early_channelinactive_lines:
    result = 'native_join_prefanout_closefuture_points_away_from_remote_channelinactive_and_toward_earlier_java_closefuture_path'

source_early_listener = ('addEarlyCloseFutureHintListener' in transport) and ('closeFutureIntercepted' in transport)
source_early_channelinactive = 'earlyChannelInactive' in transport
source_message_channelinactive = 'recordCloseHint("channelInactive", null)' in handler

print(f'rust_port = {port}')
print(f'first_close_line = {first_close_idx}')
print(f'window_closefutureintercepted_count = {len(closefuture_lines)}')
print(f'window_channelinactive_count = {len(channelinactive_lines)}')
print(f'window_early_channelinactive_count = {len(early_channelinactive_lines)}')
print(f'window_explicitlocalclose_count = {len(explicit_lines)}')
print(f'source_early_closefuture_listener_sets_closefutureintercepted = {source_early_listener}')
print(f'source_early_close_hint_handler_records_early_channelinactive = {source_early_channelinactive}')
print(f'source_message_handler_records_channelinactive = {source_message_channelinactive}')
print(f'result = {result}')
